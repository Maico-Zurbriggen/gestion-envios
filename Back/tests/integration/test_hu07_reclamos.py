"""Tests de integración de HU07 — Iniciar un reclamo desde la vista pública del token.

> Yo como usuario que consulta un envío deseo iniciar un reclamo desde la vista
> pública del token, para poder gestionar un inconveniente relacionado con el
> envío consultado.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.constants.error_codes import ErrorCodes
from app.domain.constants.estados_logistica import EstadoReclamoEnum
from app.domain.rules.reclamo_rules import MAX_RECLAMOS_ACTIVOS_POR_ENVIO
from app.infrastructure.db.models import ReclamoModel

PUBLICO = "/api/v1/reclamos/seguimiento"
ADMIN = "/api/v1/admin/reclamos"


def _payload_envio(cantidad_paquetes: int = 2) -> dict:
    return {
        "remitente_nombre": "Juan Pérez",
        "remitente_documento": "30111222",
        "remitente_telefono": "+543564111111",
        "remitente_email": "juan.perez@example.com",
        "destinatario_nombre": "María Gómez",
        "destinatario_telefono": "+543564222222",
        "destinatario_email": "maria.gomez@example.com",
        "tipo_entrega": "sucursal",
        "sucursal_destino_id": 2,
        "sucursal_origen_id": 1, "terminos_aceptados": True,
        "paquetes": [
            {"descripcion": f"Caja {i + 1}", "peso_kg": 2, "largo_cm": 30, "ancho_cm": 20, "alto_cm": 10}
            for i in range(cantidad_paquetes)
        ],
    }


def _payload_reclamo(**overrides) -> dict:
    base = {
        "tipo": "DEMORA",
        "descripcion": "El envío figura sin movimientos desde hace una semana.",
        "contacto_nombre": "María Gómez",
        "contacto_email": "maria.gomez@example.com",
    }
    base.update(overrides)
    return base


async def _registrar_envio(client: AsyncClient, cantidad_paquetes: int = 2) -> dict:
    resp = await client.post("/api/v1/envios", json=_payload_envio(cantidad_paquetes))
    assert resp.status_code == 201
    return resp.json()["data"]


# --- Escenario 1: acceso a reclamo desde seguimiento ---


@pytest.mark.asyncio
async def test_hu07_escenario_1_acceso_a_reclamo_desde_seguimiento(client: AsyncClient):
    """HU07 Escenario 1: con un token válido, al seleccionar la opción de reclamo
    el sistema habilita el inicio del reclamo para el envío consultado."""
    envio = await _registrar_envio(client)
    token = envio["token_seguimiento"]

    # El usuario accedió al envío mediante un token válido (HU04)...
    assert (await client.get(f"/api/v1/seguimiento/{token}")).status_code == 200

    # ...y selecciona la opción para realizar un reclamo.
    resp = await client.get(f"{PUBLICO}/{token}")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["token_seguimiento"] == token
    assert data["puede_iniciar"] is True
    assert data["motivo_no_habilitado"] is None
    assert data["max_reclamos_activos"] == MAX_RECLAMOS_ACTIVOS_POR_ENVIO
    assert [t["codigo"] for t in data["tipos_reclamo"]] == ["DEMORA", "DANIO", "EXTRAVIO", "OTRO"]
    assert all(t["descripcion"] for t in data["tipos_reclamo"])
    assert [p["numero_paquete"] for p in data["paquetes"]] == [p["numero_paquete"] for p in envio["paquetes"]]
    assert data["reclamos"] == []


@pytest.mark.asyncio
async def test_hu07_escenario_1_el_reclamo_queda_asociado_al_envio_consultado(
    client: AsyncClient, db_session: AsyncSession
):
    envio = await _registrar_envio(client)
    token = envio["token_seguimiento"]

    resp = await client.post(f"{PUBLICO}/{token}", json=_payload_reclamo())

    assert resp.status_code == 201
    cuerpo = resp.json()
    assert cuerpo["status"] == "success"
    data = cuerpo["data"]
    assert data["tipo"] == "DEMORA"
    assert data["estado"] == EstadoReclamoEnum.ABIERTO.value
    assert data["numero_paquete"] is None
    assert data["resolucion"] is None
    assert data["fecha_creacion"] and data["ultima_actualizacion"]
    # La vista pública no expone los datos de contacto
    assert "contacto_email" not in data

    reclamo = (await db_session.execute(select(ReclamoModel))).scalar_one()
    assert str(reclamo.envio_id) == envio["id"]
    assert reclamo.contacto_email == "maria.gomez@example.com"

    # Queda visible en la vista pública del mismo token
    inicio = await client.get(f"{PUBLICO}/{token}")
    assert [r["id"] for r in inicio.json()["data"]["reclamos"]] == [data["id"]]


@pytest.mark.asyncio
async def test_hu07_token_inexistente_no_habilita_el_reclamo(client: AsyncClient):
    resp_get = await client.get(f"{PUBLICO}/ENV-NOEXISTE00")
    assert resp_get.status_code == 404
    assert resp_get.json()["code"] == ErrorCodes.NOT_FOUND

    resp_post = await client.post(f"{PUBLICO}/ENV-NOEXISTE00", json=_payload_reclamo())
    assert resp_post.status_code == 404


@pytest.mark.asyncio
async def test_hu07_acepta_el_token_en_minusculas(client: AsyncClient):
    envio = await _registrar_envio(client)

    resp = await client.post(f"{PUBLICO}/{envio['token_seguimiento'].lower()}", json=_payload_reclamo())

    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_hu07_reclamo_sobre_un_paquete_puntual(client: AsyncClient):
    envio = await _registrar_envio(client)
    numero = envio["paquetes"][1]["numero_paquete"]

    resp = await client.post(
        f"{PUBLICO}/{envio['token_seguimiento']}",
        json=_payload_reclamo(tipo="danio", numero_paquete=f" {numero.lower()} "),
    )

    assert resp.status_code == 201
    assert resp.json()["data"]["tipo"] == "DANIO"
    assert resp.json()["data"]["numero_paquete"] == numero


@pytest.mark.asyncio
async def test_hu07_rechaza_un_paquete_de_otro_envio(client: AsyncClient):
    envio = await _registrar_envio(client)
    otro = await _registrar_envio(client, cantidad_paquetes=1)

    resp = await client.post(
        f"{PUBLICO}/{envio['token_seguimiento']}",
        json=_payload_reclamo(numero_paquete=otro["paquetes"][0]["numero_paquete"]),
    )

    assert resp.status_code == 400
    assert resp.json()["errors"][0]["field"] == "numero_paquete"


@pytest.mark.asyncio
async def test_hu07_exige_un_medio_de_contacto(client: AsyncClient):
    envio = await _registrar_envio(client)

    resp = await client.post(
        f"{PUBLICO}/{envio['token_seguimiento']}",
        json=_payload_reclamo(contacto_email=None, contacto_telefono="  "),
    )

    assert resp.status_code == 400
    assert resp.json()["code"] == ErrorCodes.VALIDATION_ERROR
    assert resp.json()["errors"][0]["field"] == "contacto"

    solo_telefono = await client.post(
        f"{PUBLICO}/{envio['token_seguimiento']}",
        json=_payload_reclamo(contacto_email=None, contacto_telefono="+54 9 3564 222222"),
    )
    assert solo_telefono.status_code == 201


@pytest.mark.asyncio
async def test_hu07_valida_el_formato_del_reclamo(client: AsyncClient):
    envio = await _registrar_envio(client)

    resp = await client.post(
        f"{PUBLICO}/{envio['token_seguimiento']}",
        json=_payload_reclamo(tipo="ROBO", descripcion="Muy corto", contacto_email="no-es-email"),
    )

    assert resp.status_code == 400
    campos = {e["field"] for e in resp.json()["errors"]}
    assert {"tipo", "descripcion", "contacto_email"} <= campos


@pytest.mark.asyncio
async def test_hu07_rechaza_un_reclamo_duplicado_en_curso(client: AsyncClient):
    envio = await _registrar_envio(client)
    url = f"{PUBLICO}/{envio['token_seguimiento']}"

    assert (await client.post(url, json=_payload_reclamo())).status_code == 201

    duplicado = await client.post(url, json=_payload_reclamo(descripcion="Sigo esperando el paquete, sin novedades."))
    assert duplicado.status_code == 409
    assert duplicado.json()["code"] == ErrorCodes.DUPLICATE_ENTRY

    # Otro motivo sí se puede reclamar
    otro_tipo = await client.post(url, json=_payload_reclamo(tipo="OTRO"))
    assert otro_tipo.status_code == 201


@pytest.mark.asyncio
async def test_hu07_tope_de_reclamos_activos_por_envio(client: AsyncClient, db_session: AsyncSession):
    envio = await _registrar_envio(client)
    token = envio["token_seguimiento"]
    for _ in range(MAX_RECLAMOS_ACTIVOS_POR_ENVIO):
        db_session.add(
            ReclamoModel(
                envio_id=uuid.UUID(envio["id"]),
                tipo="OTRO",
                descripcion="Reclamo de prueba precargado en la base.",
                contacto_nombre="Tester",
                contacto_email="tester@example.com",
                estado=EstadoReclamoEnum.EN_REVISION.value,
            )
        )
    await db_session.commit()

    inicio = await client.get(f"{PUBLICO}/{token}")
    assert inicio.json()["data"]["puede_iniciar"] is False
    assert inicio.json()["data"]["motivo_no_habilitado"]

    resp = await client.post(f"{PUBLICO}/{token}", json=_payload_reclamo())
    assert resp.status_code == 400
    assert resp.json()["errors"][0]["field"] == "token"


# --- Gestión interna del reclamo ---


@pytest.mark.asyncio
async def test_hu07_gestion_requiere_rol_administrativo(
    client: AsyncClient, vendedor_token: str, repartidor_token: str, administrativo_token: str, superadmin_token: str
):
    assert (await client.get(ADMIN)).status_code == 401
    for token in (vendedor_token, repartidor_token):
        resp = await client.get(ADMIN, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
    assert (await client.get(ADMIN, headers={"Authorization": f"Bearer {administrativo_token}"}, params={"sucursal_id": 1})).status_code == 200


@pytest.mark.asyncio
async def test_hu07_bandeja_muestra_contacto_y_filtra(client: AsyncClient, administrativo_token: str):
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    envio_a = await _registrar_envio(client)
    envio_b = await _registrar_envio(client)
    await client.post(f"{PUBLICO}/{envio_a['token_seguimiento']}", json=_payload_reclamo())
    await client.post(f"{PUBLICO}/{envio_b['token_seguimiento']}", json=_payload_reclamo(tipo="EXTRAVIO"))

    todos = await client.get(ADMIN, headers=headers, params={"sucursal_id": 1})
    assert todos.json()["total"] == 2
    primero = todos.json()["data"][0]
    assert primero["contacto_email"] == "maria.gomez@example.com"
    assert primero["remitente_nombre"] == "Juan Pérez"

    por_tipo = await client.get(ADMIN, headers=headers, params={"sucursal_id": 1, "tipo": "extravio"})
    assert por_tipo.json()["total"] == 1
    assert por_tipo.json()["data"][0]["token_seguimiento"] == envio_b["token_seguimiento"]

    por_token = await client.get(ADMIN, headers=headers, params={"sucursal_id": 1, "token": envio_a["token_seguimiento"].lower()})
    assert por_token.json()["total"] == 1

    por_estado = await client.get(ADMIN, headers=headers, params={"sucursal_id": 1, "estado": "RESUELTO"})
    assert por_estado.json()["total"] == 0

    invalido = await client.get(ADMIN, headers=headers, params={"sucursal_id": 1, "estado": "CERRADO"})
    assert invalido.status_code == 400


@pytest.mark.asyncio
async def test_hu07_ciclo_de_gestion_hasta_resolver(
    client: AsyncClient, administrativo_token: str, administrativo_usuario
):
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    envio = await _registrar_envio(client)
    token = envio["token_seguimiento"]
    creado = (await client.post(f"{PUBLICO}/{token}", json=_payload_reclamo())).json()["data"]

    en_revision = await client.patch(f"{ADMIN}/{creado['id']}/estado", headers=headers, json={"estado": "en_revision"})
    assert en_revision.status_code == 200
    assert en_revision.json()["data"]["estado"] == EstadoReclamoEnum.EN_REVISION.value
    assert en_revision.json()["data"]["usuario_resolucion_nombre"] == administrativo_usuario.nombre

    sin_resolucion = await client.patch(f"{ADMIN}/{creado['id']}/estado", headers=headers, json={"estado": "RESUELTO"})
    assert sin_resolucion.status_code == 400
    assert sin_resolucion.json()["errors"][0]["field"] == "resolucion"

    resuelto = await client.patch(
        f"{ADMIN}/{creado['id']}/estado",
        headers=headers,
        json={"estado": "RESUELTO", "resolucion": "El paquete se despachó hoy en el primer recorrido."},
    )
    assert resuelto.status_code == 200
    assert resuelto.json()["message"] == "Reclamo cerrado correctamente."

    # La respuesta se ve en la vista pública del token
    publico = await client.get(f"{PUBLICO}/{token}")
    reclamo_publico = publico.json()["data"]["reclamos"][0]
    assert reclamo_publico["estado"] == EstadoReclamoEnum.RESUELTO.value
    assert reclamo_publico["resolucion"] == "El paquete se despachó hoy en el primer recorrido."

    # Cerrado: no admite más cambios
    reabrir = await client.patch(f"{ADMIN}/{creado['id']}/estado", headers=headers, json={"estado": "EN_REVISION"})
    assert reabrir.status_code == 400

    # Al cerrarse deja de contar como duplicado: se puede volver a reclamar
    nuevo = await client.post(f"{PUBLICO}/{token}", json=_payload_reclamo())
    assert nuevo.status_code == 201


@pytest.mark.asyncio
async def test_hu07_detalle_y_404(client: AsyncClient, administrativo_token: str):
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    envio = await _registrar_envio(client)
    creado = (await client.post(f"{PUBLICO}/{envio['token_seguimiento']}", json=_payload_reclamo())).json()["data"]

    detalle = await client.get(f"{ADMIN}/{creado['id']}", headers=headers)
    assert detalle.status_code == 200
    assert detalle.json()["data"]["descripcion"] == _payload_reclamo()["descripcion"]

    assert (await client.get(f"{ADMIN}/{uuid.uuid4()}", headers=headers)).status_code == 404
    assert (await client.get(f"{ADMIN}/no-es-uuid", headers=headers)).status_code == 400
    no_existe = await client.patch(f"{ADMIN}/{uuid.uuid4()}/estado", headers=headers, json={"estado": "EN_REVISION"})
    assert no_existe.status_code == 404
