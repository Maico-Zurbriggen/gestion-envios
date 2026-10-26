"""Tests de integración de HU10 — Generar recorridos automáticamente, visualizarlos y editarlos.

> Yo como personal de logística / administración deseo generar recorridos
> automáticamente, visualizarlos y editarlos manualmente, para organizar la
> distribución de paquetes y detectar domicilios que queden fuera de un recorrido.

Sucursales del conftest: 1 = Córdoba (-31.4, -64.18), 2 = Rosario (-32.95, -60.69).
"""

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.constants.error_codes import ErrorCodes
from app.domain.constants.estados_logistica import (
    EstadoPaqueteEnum,
    EstadoRecorridoEnum,
    MotivoAlertaRecorridoEnum,
)
from app.domain.constants.roles import RolIdEnum
from app.infrastructure.auth.hasher import HasherContrasenas
from app.infrastructure.db.models import (
    AlertaRecorridoModel,
    EnvioModel,
    HistorialEstadoPaqueteModel,
    PaqueteModel,
    RecorridoModel,
    RepartidorModel,
    SucursalModel,
    UsuarioModel,
)

BASE = "/api/v1/recorridos"
CORDOBA = (-31.4, -64.18)
EN_SUCURSAL_ORIGEN = EstadoPaqueteEnum.EN_SUCURSAL_ORIGEN.value

_contador = {"n": 0}


def _siguiente() -> int:
    _contador["n"] += 1
    return _contador["n"]


async def _crear_paquete(
    db: AsyncSession,
    *,
    tipo_entrega: str = "domicilio",
    ciudad: str | None = "Córdoba",
    provincia: str | None = "Córdoba",
    latitud: float | None = None,
    longitud: float | None = None,
    sucursal_destino_id: int | None = None,
    estado: str = EN_SUCURSAL_ORIGEN,
    sucursal_actual_id: int | None = 1,
    cantidad: int = 1,
) -> list[PaqueteModel]:
    """Un envío ya recibido en una terminal (HU06), con uno o más paquetes."""
    n = _siguiente()
    envio = EnvioModel(
        remitente_nombre="Carlos Remitente",
        remitente_documento="30111222",
        remitente_telefono="+543564111222",
        remitente_email="carlos@test.com",
        destinatario_nombre=f"Destinatario {n}",
        destinatario_telefono="+543564333444",
        destinatario_email="destino@test.com",
        tipo_entrega=tipo_entrega,
        provincia_destino=provincia if tipo_entrega == "domicilio" else None,
        ciudad_destino=ciudad if tipo_entrega == "domicilio" else None,
        direccion_destino=f"Calle {n} 100" if tipo_entrega == "domicilio" else None,
        latitud_destino=latitud,
        longitud_destino=longitud,
        sucursal_destino_id=sucursal_destino_id,
        terminos_aceptados=True,
        token_seguimiento=f"ENV-REC{n:07d}",
    )
    db.add(envio)
    await db.commit()
    paquetes = []
    for i in range(cantidad):
        paquete = PaqueteModel(
            envio_id=envio.id,
            numero_paquete=f"PAQ-R{n:05d}{i:04d}",
            descripcion="Caja",
            peso_kg=2.0,
            largo_cm=20.0,
            ancho_cm=20.0,
            alto_cm=20.0,
            estado=estado,
            sucursal_actual_id=sucursal_actual_id,
        )
        db.add(paquete)
        paquetes.append(paquete)
    await db.commit()
    for paquete in paquetes:
        await db.refresh(paquete)
    return paquetes


async def _domicilio(db: AsyncSession, dlat: float, dlon: float, **kwargs) -> PaqueteModel:
    return (await _crear_paquete(db, latitud=CORDOBA[0] + dlat, longitud=CORDOBA[1] + dlon, **kwargs))[0]


async def _crear_repartidor(
    db: AsyncSession, nombre: str, *, sucursal_id: int = 1, tipo: str = "CORTA", activo: bool = True
) -> UsuarioModel:
    n = _siguiente()
    usuario = UsuarioModel(
        nombre=nombre,
        dni=f"40{n:06d}",
        email=f"repartidor{n}@empresa.com",
        telefono="+543564000111",
        password_hash=HasherContrasenas.generar_hash("Repartidor123!*"),
        estado="Activo",
        requiere_cambio_password=False,
        rol_id=RolIdEnum.REPARTIDOR.value,
    )
    db.add(usuario)
    await db.commit()
    db.add(RepartidorModel(usuario_id=usuario.id, sucursal_base_id=sucursal_id, tipo_reparto=tipo, activo=activo))
    await db.commit()
    await db.refresh(usuario)
    return usuario


def _numeros(recorrido: dict) -> list[str]:
    return [p["numero_paquete"] for parada in recorrido["paradas"] for p in parada["paquetes"]]


async def _generar(client: AsyncClient, token: str, **datos) -> dict:
    cuerpo = {"sucursal_id": 1, "tipo_distancia": "CORTA", **datos}
    resp = await client.post(f"{BASE}/generar", headers={"Authorization": f"Bearer {token}"}, json=cuerpo)
    assert resp.status_code == 200, resp.text
    return resp.json()


# --- Seguridad ---


@pytest.mark.asyncio
async def test_hu10_recorridos_requieren_rol_de_logistica(
    client: AsyncClient, vendedor_token: str, repartidor_token: str, administrativo_token: str, superadmin_token: str
):
    cuerpo = {"sucursal_id": 1, "tipo_distancia": "CORTA"}
    assert (await client.post(f"{BASE}/generar", json=cuerpo)).status_code == 401
    for token in (vendedor_token, repartidor_token):
        resp = await client.post(f"{BASE}/generar", headers={"Authorization": f"Bearer {token}"}, json=cuerpo)
        assert resp.status_code == 403
        assert resp.json()["code"] == ErrorCodes.FORBIDDEN_ACCESS
    assert (await client.get(BASE, headers={"Authorization": f"Bearer {administrativo_token}"})).status_code == 200


# --- Escenario 1: generación automática ---


@pytest.mark.asyncio
async def test_hu10_escenario_1_generacion_equitativa_por_zonas(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str
):
    """HU10 Escenario 1: considera la sucursal de partida, optimiza el tiempo y
    distribuye los paquetes de forma aproximadamente equitativa entre repartidores."""
    norte = [await _domicilio(db_session, 0.02 + i * 0.002, 0.001 * i) for i in range(3)]
    sur = [await _domicilio(db_session, -0.02 - i * 0.002, 0.001 * i) for i in range(3)]
    await _crear_repartidor(db_session, "Ana Repartidora")
    await _crear_repartidor(db_session, "Bruno Repartidor")

    cuerpo = await _generar(client, administrativo_token, orientacion_calles_grados=15)

    data = cuerpo["data"]
    assert data["resumen"] == {
        "paquetes_pendientes": 6,
        "paquetes_asignados": 6,
        "paquetes_sin_recorrido": 0,
        "repartidores_disponibles": 2,
        "recorridos_generados": 2,
        "recorridos_reemplazados": 0,
    }
    assert data["alertas"] == []
    assert data["orientacion_calles_grados"] == 15

    numeros_norte = {p.numero_paquete for p in norte}
    numeros_sur = {p.numero_paquete for p in sur}
    for recorrido in data["recorridos"]:
        assert recorrido["estado"] == EstadoRecorridoEnum.GENERADO.value
        assert recorrido["generado_automaticamente"] is True
        assert recorrido["tipo_distancia"] == "CORTA"
        assert recorrido["cantidad_paquetes"] == 3
        assert recorrido["distancia_estimada_km"] > 0
        assert recorrido["duracion_estimada_min"] > 0
        # Cada repartidor recibe una sola zona (todo norte o todo sur)
        assert set(_numeros(recorrido)) in (numeros_norte, numeros_sur)
        # Arranca y termina en la sucursal de partida
        assert recorrido["sucursal_origen"]["id"] == 1
        assert recorrido["vuelve_a_sucursal"] is True
        inicio, fin = recorrido["trazado"][0], recorrido["trazado"][-1]
        assert (inicio["latitud"], inicio["longitud"]) == CORDOBA == (fin["latitud"], fin["longitud"])
        assert len(recorrido["trazado"]) == 3 + 2
        assert [p["orden"] for p in recorrido["paradas"]] == [1, 2, 3]
        assert all(p["tipo_parada"] == "DOMICILIO" for p in recorrido["paradas"])

    repartidores = {r["repartidor"]["nombre"] for r in data["recorridos"]}
    assert repartidores == {"Ana Repartidora", "Bruno Repartidor"}


@pytest.mark.asyncio
async def test_hu10_escenario_1_orden_de_visita_optimizado(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str
):
    """El recorrido visita las paradas en cadena (cercana a cercana), no en el orden de carga."""
    lejos = await _domicilio(db_session, 0.03, 0.0)
    cerca = await _domicilio(db_session, 0.01, 0.0)
    medio = await _domicilio(db_session, 0.02, 0.0)
    await _crear_repartidor(db_session, "Ana Repartidora")

    recorrido = (await _generar(client, administrativo_token))["data"]["recorridos"][0]

    assert _numeros(recorrido) in (
        [cerca.numero_paquete, medio.numero_paquete, lejos.numero_paquete],
        [lejos.numero_paquete, medio.numero_paquete, cerca.numero_paquete],
    )


@pytest.mark.asyncio
async def test_hu10_paquetes_del_mismo_domicilio_comparten_parada(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str
):
    await _crear_paquete(db_session, latitud=-31.41, longitud=-64.19, cantidad=3)
    await _crear_repartidor(db_session, "Ana Repartidora")

    recorrido = (await _generar(client, administrativo_token))["data"]["recorridos"][0]

    assert recorrido["cantidad_paradas"] == 1
    assert recorrido["cantidad_paquetes"] == 3
    assert len(recorrido["paradas"][0]["paquetes"]) == 3


@pytest.mark.asyncio
async def test_hu10_solo_considera_paquetes_listos_en_la_sucursal(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str
):
    listo = await _domicilio(db_session, 0.01, 0.01)
    await _domicilio(db_session, 0.01, 0.02, estado="Pendiente", sucursal_actual_id=None)  # no recibido
    await _domicilio(db_session, 0.01, 0.03, sucursal_actual_id=2)  # en otra sucursal
    await _domicilio(db_session, 0.01, 0.04, estado=EstadoPaqueteEnum.EN_REPARTO.value)  # ya salió
    reintento = await _domicilio(db_session, 0.02, 0.01, estado=EstadoPaqueteEnum.ENTREGA_FALLIDA.value)
    await _crear_repartidor(db_session, "Ana Repartidora")

    recorrido = (await _generar(client, administrativo_token))["data"]["recorridos"][0]

    assert set(_numeros(recorrido)) == {listo.numero_paquete, reintento.numero_paquete}


# --- Escenario 4: tipos de reparto ---


@pytest.mark.asyncio
async def test_hu10_escenario_4_corta_y_larga_distancia(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str
):
    """HU10 Escenario 4: corta distancia = entregas dentro de la misma ciudad;
    larga distancia = trayectos entre ciudades dejando paquetes en sucursales."""
    local = await _domicilio(db_session, 0.01, 0.01)
    a_rosario_domicilio = (
        await _crear_paquete(db_session, ciudad="Rosario", provincia="Santa Fe", latitud=-32.94, longitud=-60.65)
    )[0]
    a_rosario_retiro = (await _crear_paquete(db_session, tipo_entrega="sucursal", sucursal_destino_id=2))[0]
    await _crear_paquete(db_session, tipo_entrega="sucursal", sucursal_destino_id=1)  # ya está donde se retira
    await _crear_repartidor(db_session, "Corta Distancia", tipo="CORTA")
    await _crear_repartidor(db_session, "Larga Distancia", tipo="LARGA")

    corta = (await _generar(client, administrativo_token))["data"]
    assert corta["resumen"]["paquetes_pendientes"] == 1
    assert _numeros(corta["recorridos"][0]) == [local.numero_paquete]
    assert corta["recorridos"][0]["repartidor"]["nombre"] == "Corta Distancia"

    larga = (await _generar(client, administrativo_token, tipo_distancia="LARGA"))["data"]
    assert larga["resumen"]["paquetes_pendientes"] == 2
    recorrido = larga["recorridos"][0]
    assert recorrido["repartidor"]["nombre"] == "Larga Distancia"
    assert recorrido["vuelve_a_sucursal"] is False
    # Ambos paquetes se dejan en la sucursal de Rosario: una sola parada
    assert recorrido["cantidad_paradas"] == 1
    parada = recorrido["paradas"][0]
    assert parada["tipo_parada"] == "SUCURSAL"
    assert parada["sucursal_destino"]["id"] == 2
    assert set(_numeros(recorrido)) == {a_rosario_domicilio.numero_paquete, a_rosario_retiro.numero_paquete}
    assert len(recorrido["trazado"]) == 2  # origen -> sucursal destino, sin vuelta
    assert recorrido["distancia_estimada_km"] > 300


@pytest.mark.asyncio
async def test_hu10_domicilio_de_localidad_sin_sucursal_lo_reparte_la_mas_cercana(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str
):
    """Villa Carlos Paz no tiene sucursal: la atiende Córdoba con un recorrido corto."""
    paquete = (
        await _crear_paquete(db_session, ciudad="Villa Carlos Paz", latitud=-31.42, longitud=-64.50)
    )[0]
    await _crear_repartidor(db_session, "Ana Repartidora")

    recorrido = (await _generar(client, administrativo_token))["data"]["recorridos"][0]

    assert _numeros(recorrido) == [paquete.numero_paquete]


# --- Escenario 3: domicilio sin recorrido ---


@pytest.mark.asyncio
async def test_hu10_escenario_3_alerta_por_domicilio_sin_ubicacion(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str
):
    """HU10 Escenario 3: si al finalizar la generación queda un domicilio sin
    recorrido, el sistema genera una alerta."""
    ubicado = await _domicilio(db_session, 0.01, 0.01)
    sin_ubicacion = (await _crear_paquete(db_session))[0]  # domicilio sin marcar en el mapa
    await _crear_repartidor(db_session, "Ana Repartidora")

    data = (await _generar(client, administrativo_token))["data"]

    assert _numeros(data["recorridos"][0]) == [ubicado.numero_paquete]
    assert data["resumen"]["paquetes_sin_recorrido"] == 1
    alerta = data["alertas"][0]
    assert alerta["numero_paquete"] == sin_ubicacion.numero_paquete
    assert alerta["motivo"] == MotivoAlertaRecorridoEnum.SIN_UBICACION_DESTINO.value
    assert alerta["descripcion_motivo"]
    assert alerta["resuelta"] is False
    assert "Córdoba" in alerta["destino"]

    listado = await client.get(
        f"{BASE}/alertas", headers={"Authorization": f"Bearer {administrativo_token}"}, params={"sucursal_id": 1}
    )
    assert listado.json()["total"] == 1


@pytest.mark.asyncio
async def test_hu10_escenario_3_alerta_sin_repartidores_y_se_resuelve_al_regenerar(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str
):
    paquetes = [await _domicilio(db_session, 0.01 * i, 0.01) for i in (1, 2)]

    sin_repartidores = (await _generar(client, administrativo_token))["data"]
    assert sin_repartidores["recorridos"] == []
    assert sin_repartidores["resumen"]["repartidores_disponibles"] == 0
    assert {a["motivo"] for a in sin_repartidores["alertas"]} == {
        MotivoAlertaRecorridoEnum.SIN_REPARTIDOR_DISPONIBLE.value
    }
    assert len(sin_repartidores["alertas"]) == 2

    await _crear_repartidor(db_session, "Ana Repartidora")
    con_repartidor = (await _generar(client, administrativo_token))["data"]
    assert con_repartidor["alertas"] == []
    assert set(_numeros(con_repartidor["recorridos"][0])) == {p.numero_paquete for p in paquetes}

    alertas = (await db_session.execute(select(AlertaRecorridoModel))).scalars().all()
    assert len(alertas) == 2
    assert all(a.resuelta and a.resuelta_at for a in alertas)


@pytest.mark.asyncio
async def test_hu10_alerta_no_se_duplica_entre_generaciones(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str
):
    await _crear_paquete(db_session)  # sin ubicación
    await _generar(client, administrativo_token)
    await _generar(client, administrativo_token)

    alertas = (await db_session.execute(select(AlertaRecorridoModel))).scalars().all()
    assert len(alertas) == 1


@pytest.mark.asyncio
async def test_hu10_resolver_alerta_manualmente(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str
):
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    await _crear_paquete(db_session)
    alerta = (await _generar(client, administrativo_token))["data"]["alertas"][0]

    resp = await client.patch(f"{BASE}/alertas/{alerta['id']}/resolver", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["resuelta"] is True
    assert resp.json()["data"]["resuelta_at"] is not None

    assert (await client.patch(f"{BASE}/alertas/{alerta['id']}/resolver", headers=headers)).status_code == 400
    assert (await client.patch(f"{BASE}/alertas/{uuid.uuid4()}/resolver", headers=headers)).status_code == 404

    pendientes = await client.get(f"{BASE}/alertas", headers=headers)
    assert pendientes.json()["total"] == 0
    todas = await client.get(f"{BASE}/alertas", headers=headers, params={"incluir_resueltas": True})
    assert todas.json()["total"] == 1


# --- Regeneración ---


@pytest.mark.asyncio
async def test_hu10_regenerar_exige_confirmacion_y_reemplaza(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str
):
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    await _domicilio(db_session, 0.01, 0.01)
    await _crear_repartidor(db_session, "Ana Repartidora")
    primero = (await _generar(client, administrativo_token))["data"]["recorridos"][0]

    repetido = await client.post(f"{BASE}/generar", headers=headers, json={"sucursal_id": 1, "tipo_distancia": "CORTA"})
    assert repetido.status_code == 409
    assert repetido.json()["code"] == ErrorCodes.DUPLICATE_ENTRY

    reemplazo = (await _generar(client, administrativo_token, reemplazar_existentes=True))["data"]
    assert reemplazo["resumen"]["recorridos_reemplazados"] == 1
    assert reemplazo["recorridos"][0]["id"] != primero["id"]
    assert (await client.get(f"{BASE}/{primero['id']}", headers=headers)).status_code == 404

    # Otra fecha no choca con la generación de hoy
    manana = (date.today() + timedelta(days=1)).isoformat()
    otro_dia = await client.post(
        f"{BASE}/generar", headers=headers, json={"sucursal_id": 1, "tipo_distancia": "CORTA", "fecha": manana}
    )
    assert otro_dia.status_code == 200
    # El paquete ya está en el recorrido de hoy: no se asigna dos veces
    assert otro_dia.json()["data"]["resumen"]["paquetes_pendientes"] == 0


@pytest.mark.asyncio
async def test_hu10_generacion_con_repartidores_elegidos(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str
):
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    for i in range(4):
        await _domicilio(db_session, 0.01 * (i + 1), 0.0)
    elegido = await _crear_repartidor(db_session, "Elegido")
    await _crear_repartidor(db_session, "No elegido")
    larga = await _crear_repartidor(db_session, "De larga", tipo="LARGA")

    data = (await _generar(client, administrativo_token, repartidor_ids=[str(elegido.id)]))["data"]
    assert len(data["recorridos"]) == 1
    assert data["recorridos"][0]["repartidor"]["usuario_id"] == str(elegido.id)

    invalido = await client.post(
        f"{BASE}/generar",
        headers=headers,
        json={"sucursal_id": 1, "tipo_distancia": "CORTA", "repartidor_ids": [str(larga.id)], "reemplazar_existentes": True},
    )
    assert invalido.status_code == 400
    assert invalido.json()["errors"][0]["field"] == "repartidor_ids[0]"


@pytest.mark.asyncio
async def test_hu10_generacion_valida_los_datos(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str
):
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    db_session.add(SucursalModel(id=3, nombre="Sucursal Sin Mapa", provincia="Salta", ciudad="Salta", direccion="X 1"))
    await db_session.commit()

    casos = [
        ({"sucursal_id": 999, "tipo_distancia": "CORTA"}, "sucursal_id"),
        ({"sucursal_id": 3, "tipo_distancia": "CORTA"}, "sucursal_id"),
        ({"sucursal_id": 1, "tipo_distancia": "MEDIA"}, "tipo_distancia"),
        ({"sucursal_id": 1, "tipo_distancia": "CORTA", "orientacion_calles_grados": 90}, "orientacion_calles_grados"),
    ]
    for cuerpo, campo in casos:
        resp = await client.post(f"{BASE}/generar", headers=headers, json=cuerpo)
        assert resp.status_code == 400, cuerpo
        assert resp.json()["errors"][0]["field"] == campo


# --- Escenario 2: visualización y edición manual ---


@pytest.mark.asyncio
async def test_hu10_escenario_2_visualizar_y_listar(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str
):
    """HU10 Escenario 2: el sistema permite visualizar el recorrido generado."""
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    await _domicilio(db_session, 0.01, 0.01)
    await _crear_repartidor(db_session, "Ana Repartidora")
    generado = (await _generar(client, administrativo_token))["data"]["recorridos"][0]

    detalle = await client.get(f"{BASE}/{generado['id']}", headers=headers)
    assert detalle.status_code == 200
    data = detalle.json()["data"]
    assert data["id"] == generado["id"]
    parada = data["paradas"][0]
    assert parada["latitud"] is not None and parada["longitud"] is not None
    paquete = parada["paquetes"][0]
    assert paquete["destinatario_telefono"] == "+543564333444"
    assert paquete["estado_en_recorrido"] == "PENDIENTE"
    assert paquete["token_seguimiento"].startswith("ENV-")

    listado = await client.get(BASE, headers=headers, params={"sucursal_id": 1, "fecha": date.today().isoformat()})
    assert listado.json()["total"] == 1
    assert listado.json()["data"][0]["cantidad_paquetes"] == 1
    assert (await client.get(BASE, headers=headers, params={"tipo_distancia": "LARGA"})).json()["total"] == 0
    assert (await client.get(BASE, headers=headers, params={"estado": "CERRADO"})).status_code == 400
    assert (await client.get(f"{BASE}/{uuid.uuid4()}", headers=headers)).status_code == 404


@pytest.mark.asyncio
async def test_hu10_escenario_2_edicion_manual_reordena_quita_y_alerta(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str
):
    """HU10 Escenarios 2 y 3: la edición manual cambia el recorrido y, al terminar
    el control, los domicilios que quedaron afuera generan una alerta."""
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    a = await _domicilio(db_session, 0.01, 0.0)
    b = await _domicilio(db_session, 0.02, 0.0)
    c = await _domicilio(db_session, 0.03, 0.0)
    await _crear_repartidor(db_session, "Ana Repartidora")
    recorrido = (await _generar(client, administrativo_token))["data"]["recorridos"][0]

    # Reordenar y quitar C
    resp = await client.put(
        f"{BASE}/{recorrido['id']}/paquetes",
        headers=headers,
        json={"paquetes": [b.numero_paquete, a.numero_paquete.lower()]},
    )
    assert resp.status_code == 200, resp.text
    cuerpo = resp.json()
    editado = cuerpo["data"]
    assert editado["estado"] == EstadoRecorridoEnum.EN_EDICION.value
    assert editado["generado_automaticamente"] is False
    assert _numeros(editado) == [b.numero_paquete, a.numero_paquete]
    assert editado["distancia_estimada_km"] != recorrido["distancia_estimada_km"]
    # C quedó afuera: alerta
    assert [al["numero_paquete"] for al in cuerpo["alertas"]] == [c.numero_paquete]
    assert cuerpo["alertas"][0]["motivo"] == MotivoAlertaRecorridoEnum.SIN_RECORRIDO_ASIGNADO.value
    assert cuerpo["alertas"][0]["recorrido_id"] == recorrido["id"]

    # Volver a agregarlo (por UUID) resuelve la alerta
    resp_agregar = await client.put(
        f"{BASE}/{recorrido['id']}/paquetes",
        headers=headers,
        json={"paquetes": [b.numero_paquete, a.numero_paquete, str(c.id)]},
    )
    assert resp_agregar.status_code == 200
    assert resp_agregar.json()["alertas"] == []
    alerta = (await db_session.execute(select(AlertaRecorridoModel))).scalar_one()
    await db_session.refresh(alerta)
    assert alerta.resuelta is True


@pytest.mark.asyncio
async def test_hu10_edicion_manual_permite_asignar_un_domicilio_sin_ubicacion(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str
):
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    ubicado = await _domicilio(db_session, 0.01, 0.01)
    sin_ubicacion = (await _crear_paquete(db_session))[0]
    await _crear_repartidor(db_session, "Ana Repartidora")
    recorrido = (await _generar(client, administrativo_token))["data"]["recorridos"][0]

    resp = await client.put(
        f"{BASE}/{recorrido['id']}/paquetes",
        headers=headers,
        json={"paquetes": [ubicado.numero_paquete, sin_ubicacion.numero_paquete]},
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["paquetes_sin_ubicacion"] == 1
    assert data["paradas"][1]["latitud"] is None
    assert len(data["trazado"]) == 3  # origen, parada ubicada, vuelta
    assert resp.json()["alertas"] == []


@pytest.mark.asyncio
async def test_hu10_edicion_manual_rechaza_paquetes_no_asignables(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str
):
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    propio = await _domicilio(db_session, 0.01, 0.01)
    otra_sucursal = await _domicilio(db_session, 0.01, 0.02, sucursal_actual_id=2)
    larga = (await _crear_paquete(db_session, tipo_entrega="sucursal", sucursal_destino_id=2))[0]
    no_recibido = await _domicilio(db_session, 0.01, 0.03, estado="Pendiente")
    await _crear_repartidor(db_session, "Ana Repartidora")
    recorrido = (await _generar(client, administrativo_token))["data"]["recorridos"][0]
    url = f"{BASE}/{recorrido['id']}/paquetes"

    resp = await client.put(
        url,
        headers=headers,
        json={"paquetes": [propio.numero_paquete, otra_sucursal.numero_paquete, larga.numero_paquete, no_recibido.numero_paquete]},
    )
    assert resp.status_code == 400
    mensajes = [e["message"] for e in resp.json()["errors"]]
    assert len(mensajes) == 3
    assert "sucursal de partida" in mensajes[0]
    assert "larga distancia" in mensajes[1]
    assert "Pendiente" in mensajes[2]

    inexistente = await client.put(url, headers=headers, json={"paquetes": ["PAQ-NOEXISTE00"]})
    assert inexistente.status_code == 400
    assert inexistente.json()["errors"][0]["field"] == "paquetes[0]"

    repetido = await client.put(url, headers=headers, json={"paquetes": [propio.numero_paquete, str(propio.id)]})
    assert repetido.status_code == 400

    vacio = await client.put(url, headers=headers, json={"paquetes": []})
    assert vacio.status_code == 400


@pytest.mark.asyncio
async def test_hu10_un_paquete_no_puede_estar_en_dos_recorridos(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str
):
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    norte = await _domicilio(db_session, 0.02, 0.0)
    sur = await _domicilio(db_session, -0.02, 0.0)
    await _crear_repartidor(db_session, "Ana Repartidora")
    await _crear_repartidor(db_session, "Bruno Repartidor")
    recorridos = (await _generar(client, administrativo_token))["data"]["recorridos"]
    primero, segundo = recorridos
    ajeno = sur if _numeros(primero) == [norte.numero_paquete] else norte

    resp = await client.put(
        f"{BASE}/{primero['id']}/paquetes",
        headers=headers,
        json={"paquetes": _numeros(primero) + [ajeno.numero_paquete]},
    )

    assert resp.status_code == 400
    assert "otro recorrido activo" in resp.json()["errors"][0]["message"]


@pytest.mark.asyncio
async def test_hu10_quitar_paquete_y_optimizar(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str
):
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    a = await _domicilio(db_session, 0.01, 0.0)
    b = await _domicilio(db_session, 0.02, 0.0)
    c = await _domicilio(db_session, 0.03, 0.0)
    await _crear_repartidor(db_session, "Ana Repartidora")
    recorrido = (await _generar(client, administrativo_token))["data"]["recorridos"][0]

    # Desordenar a mano y optimizar: vuelve a una cadena sin saltos
    await client.put(
        f"{BASE}/{recorrido['id']}/paquetes",
        headers=headers,
        json={"paquetes": [a.numero_paquete, c.numero_paquete, b.numero_paquete]},
    )
    optimizado = await client.post(f"{BASE}/{recorrido['id']}/optimizar", headers=headers)
    assert optimizado.status_code == 200
    orden = _numeros(optimizado.json()["data"])
    assert orden in ([a.numero_paquete, b.numero_paquete, c.numero_paquete], [c.numero_paquete, b.numero_paquete, a.numero_paquete])
    assert optimizado.json()["data"]["distancia_estimada_km"] <= recorrido["distancia_estimada_km"] + 0.01

    quitar = await client.delete(f"{BASE}/{recorrido['id']}/paquetes/{b.numero_paquete}", headers=headers)
    assert quitar.status_code == 200
    assert b.numero_paquete not in _numeros(quitar.json()["data"])
    assert quitar.json()["alertas"][0]["numero_paquete"] == b.numero_paquete

    no_esta = await client.delete(f"{BASE}/{recorrido['id']}/paquetes/{b.numero_paquete}", headers=headers)
    assert no_esta.status_code == 404

    await client.delete(f"{BASE}/{recorrido['id']}/paquetes/{a.numero_paquete}", headers=headers)
    ultimo = await client.delete(f"{BASE}/{recorrido['id']}/paquetes/{c.numero_paquete}", headers=headers)
    assert ultimo.status_code == 400


@pytest.mark.asyncio
async def test_hu10_reasignar_repartidor(client: AsyncClient, db_session: AsyncSession, administrativo_token: str):
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    await _domicilio(db_session, 0.01, 0.0)
    await _domicilio(db_session, -0.01, 0.0)
    ana = await _crear_repartidor(db_session, "Ana Repartidora")
    bruno = await _crear_repartidor(db_session, "Bruno Repartidor")
    carla = await _crear_repartidor(db_session, "Carla Repartidora", activo=False)
    larga = await _crear_repartidor(db_session, "De Larga", tipo="LARGA")
    recorridos = (await _generar(client, administrativo_token, repartidor_ids=[str(ana.id)]))["data"]["recorridos"]
    recorrido = recorridos[0]
    url = f"{BASE}/{recorrido['id']}/repartidor"

    ok = await client.patch(url, headers=headers, json={"repartidor_id": str(bruno.id)})
    assert ok.status_code == 200
    assert ok.json()["data"]["repartidor"]["nombre"] == "Bruno Repartidor"
    assert ok.json()["data"]["estado"] == EstadoRecorridoEnum.EN_EDICION.value

    for usuario in (carla, larga):
        resp = await client.patch(url, headers=headers, json={"repartidor_id": str(usuario.id)})
        assert resp.status_code == 400
    assert (await client.patch(url, headers=headers, json={"repartidor_id": str(uuid.uuid4())})).status_code == 400

    # Ana ya salió con otro recorrido ese mismo día: está ocupada
    db_session.add(
        RecorridoModel(
            repartidor_id=ana.id,
            sucursal_origen_id=1,
            tipo_distancia="CORTA",
            fecha=date.today(),
            estado=EstadoRecorridoEnum.EN_CURSO.value,
        )
    )
    await db_session.commit()
    ocupada = await client.patch(url, headers=headers, json={"repartidor_id": str(ana.id)})
    assert ocupada.status_code == 409
    assert ocupada.json()["code"] == ErrorCodes.DUPLICATE_ENTRY

    # Reasignar al mismo repartidor que ya lo tiene no cambia nada
    mismo = await client.patch(url, headers=headers, json={"repartidor_id": str(bruno.id)})
    assert mismo.status_code == 200


# --- Salida del recorrido y descarte ---


@pytest.mark.asyncio
async def test_hu10_iniciar_recorrido_despacha_los_paquetes(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str, administrativo_usuario
):
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    paquete = await _domicilio(db_session, 0.01, 0.01)
    sin_ubicacion = (await _crear_paquete(db_session))[0]
    await _crear_repartidor(db_session, "Ana Repartidora")
    recorrido = (await _generar(client, administrativo_token))["data"]["recorridos"][0]
    await client.put(
        f"{BASE}/{recorrido['id']}/paquetes",
        headers=headers,
        json={"paquetes": [paquete.numero_paquete, sin_ubicacion.numero_paquete]},
    )

    resp = await client.post(f"{BASE}/{recorrido['id']}/iniciar", headers=headers)

    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["estado"] == EstadoRecorridoEnum.EN_CURSO.value
    for p in (paquete, sin_ubicacion):
        await db_session.refresh(p)
        assert p.estado == EstadoPaqueteEnum.EN_REPARTO.value
        assert p.sucursal_actual_id is None

    historial = (
        await db_session.execute(
            select(HistorialEstadoPaqueteModel).where(HistorialEstadoPaqueteModel.paquete_id == paquete.id)
        )
    ).scalar_one()
    assert historial.estado_anterior == EN_SUCURSAL_ORIGEN
    assert historial.estado_nuevo == EstadoPaqueteEnum.EN_REPARTO.value
    assert historial.usuario_id == administrativo_usuario.id
    assert "Ana Repartidora" in historial.observacion

    # Se refleja en el seguimiento público (HU04)
    envio = await db_session.get(EnvioModel, paquete.envio_id)
    seguimiento = await client.get(f"/api/v1/seguimiento/{envio.token_seguimiento}")
    assert seguimiento.json()["data"]["paquetes"][0]["estado"] == EstadoPaqueteEnum.EN_REPARTO.value

    # En curso ya no se edita, no se reinicia ni se elimina
    assert (await client.post(f"{BASE}/{recorrido['id']}/iniciar", headers=headers)).status_code == 400
    assert (
        await client.put(f"{BASE}/{recorrido['id']}/paquetes", headers=headers, json={"paquetes": [paquete.numero_paquete]})
    ).status_code == 400
    assert (await client.delete(f"{BASE}/{recorrido['id']}", headers=headers)).status_code == 400


@pytest.mark.asyncio
async def test_hu10_iniciar_larga_distancia_pasa_a_en_transito(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str
):
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    paquete = (await _crear_paquete(db_session, tipo_entrega="sucursal", sucursal_destino_id=2))[0]
    await _crear_repartidor(db_session, "Larga Distancia", tipo="LARGA")
    recorrido = (await _generar(client, administrativo_token, tipo_distancia="LARGA"))["data"]["recorridos"][0]

    resp = await client.post(f"{BASE}/{recorrido['id']}/iniciar", headers=headers)

    assert resp.status_code == 200
    await db_session.refresh(paquete)
    assert paquete.estado == EstadoPaqueteEnum.EN_TRANSITO.value


@pytest.mark.asyncio
async def test_hu10_no_inicia_si_un_paquete_ya_no_esta_en_la_sucursal(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str
):
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    paquete = await _domicilio(db_session, 0.01, 0.01)
    await _crear_repartidor(db_session, "Ana Repartidora")
    recorrido = (await _generar(client, administrativo_token))["data"]["recorridos"][0]
    paquete.estado = EstadoPaqueteEnum.ENTREGADO_EN_SUCURSAL.value
    await db_session.commit()

    resp = await client.post(f"{BASE}/{recorrido['id']}/iniciar", headers=headers)

    assert resp.status_code == 400
    assert paquete.numero_paquete in resp.json()["errors"][0]["message"]


@pytest.mark.asyncio
async def test_hu10_eliminar_recorrido_libera_y_alerta(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str
):
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    paquete = await _domicilio(db_session, 0.01, 0.01)
    await _crear_repartidor(db_session, "Ana Repartidora")
    recorrido = (await _generar(client, administrativo_token))["data"]["recorridos"][0]

    resp = await client.delete(f"{BASE}/{recorrido['id']}", headers=headers)

    assert resp.status_code == 200
    assert [a["numero_paquete"] for a in resp.json()["alertas"]] == [paquete.numero_paquete]
    assert (await client.get(f"{BASE}/{recorrido['id']}", headers=headers)).status_code == 404

    # El paquete queda libre para una nueva generación (sin pedir reemplazo)
    nuevo = (await _generar(client, administrativo_token))["data"]
    assert _numeros(nuevo["recorridos"][0]) == [paquete.numero_paquete]
    assert nuevo["alertas"] == []


# --- Completar domicilios sin ubicación ---


async def _recorrido_con_domicilio_sin_ubicacion(client, db, token):
    ubicado = await _domicilio(db, 0.01, 0.01)
    sin_ubicacion = await _crear_paquete(db, cantidad=2)
    await _crear_repartidor(db, "Repartidor ubicación")
    recorrido = (await _generar(client, token))["data"]["recorridos"][0]
    response = await client.put(
        f"{BASE}/{recorrido['id']}/paquetes",
        headers={"Authorization": f"Bearer {token}"},
        json={"paquetes": [ubicado.numero_paquete, *(p.numero_paquete for p in sin_ubicacion)]},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"], ubicado, sin_ubicacion


@pytest.mark.asyncio
async def test_hu10_completar_ubicacion_persiste_y_actualiza_todos_los_paquetes_del_envio(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str
):
    recorrido, _, paquetes = await _recorrido_con_domicilio_sin_ubicacion(client, db_session, administrativo_token)
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    punto = {"latitud": -31.43, "longitud": -64.21}
    response = await client.patch(
        f"{BASE}/{recorrido['id']}/paquetes/{paquetes[0].numero_paquete}/ubicacion", headers=headers, json=punto
    )
    assert response.status_code == 200, response.text
    actualizado = response.json()["data"]
    assert actualizado["paquetes_sin_ubicacion"] == 0
    assert _numeros(actualizado) == _numeros(recorrido)
    assert actualizado["distancia_estimada_km"] != recorrido["distancia_estimada_km"]
    assert punto in actualizado["trazado"]
    assert actualizado["estado"] == "EN_EDICION"
    assert actualizado["generado_automaticamente"] is False
    assert len(actualizado["paradas"][-1]["paquetes"]) == 2
    envio = await db_session.get(EnvioModel, paquetes[0].envio_id)
    await db_session.refresh(envio)
    assert (envio.latitud_destino, envio.longitud_destino) == (-31.43, -64.21)
    recargado = await client.get(f"{BASE}/{recorrido['id']}", headers=headers)
    assert recargado.json()["data"]["paquetes_sin_ubicacion"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("otro_en_curso", [False, True])
async def test_hu10_ubicacion_compartida_recalcula_otros_recorridos_y_respeta_los_iniciados(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str, otro_en_curso: bool
):
    await _domicilio(db_session, 0.01, 0.01)
    await _domicilio(db_session, -0.01, -0.01)
    await _crear_repartidor(db_session, "Ana ubicación")
    await _crear_repartidor(db_session, "Bruno ubicación")
    recorridos = (await _generar(client, administrativo_token))["data"]["recorridos"]
    assert len(recorridos) == 2
    paquetes = await _crear_paquete(db_session, cantidad=2)
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    for recorrido, paquete in zip(recorridos, paquetes, strict=True):
        response = await client.put(
            f"{BASE}/{recorrido['id']}/paquetes", headers=headers,
            json={"paquetes": [*_numeros(recorrido), paquete.numero_paquete]},
        )
        assert response.status_code == 200, response.text
    if otro_en_curso:
        started = await client.post(f"{BASE}/{recorridos[1]['id']}/iniciar", headers=headers)
        assert started.status_code == 200, started.text
    response = await client.patch(
        f"{BASE}/{recorridos[0]['id']}/paquetes/{paquetes[0].numero_paquete}/ubicacion", headers=headers,
        json={"latitud": -31.43, "longitud": -64.21},
    )
    if otro_en_curso:
        assert response.status_code == 409, response.text
        envio = await db_session.get(EnvioModel, paquetes[0].envio_id)
        assert envio.latitud_destino is None
        assert envio.longitud_destino is None
    else:
        assert response.status_code == 200, response.text
        for recorrido in recorridos:
            actualizado = (await client.get(f"{BASE}/{recorrido['id']}", headers=headers)).json()["data"]
            assert actualizado["paquetes_sin_ubicacion"] == 0
            assert actualizado["distancia_estimada_km"] > recorrido["distancia_estimada_km"]


@pytest.mark.asyncio
async def test_hu10_completar_ubicacion_valida_pertenencia_coordenadas_y_estado(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str
):
    recorrido, ubicado, paquetes = await _recorrido_con_domicilio_sin_ubicacion(client, db_session, administrativo_token)
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    root = f"{BASE}/{recorrido['id']}/paquetes"
    punto = {"latitud": -31.43, "longitud": -64.21}
    assert (await client.patch(f"{root}/PAQ-NOEXISTE/ubicacion", headers=headers, json=punto)).status_code == 404
    externo = (await _crear_paquete(db_session))[0]
    assert (await client.patch(f"{root}/{externo.numero_paquete}/ubicacion", headers=headers, json=punto)).status_code == 404
    assert (await client.patch(f"{root}/{ubicado.numero_paquete}/ubicacion", headers=headers, json=punto)).status_code == 409
    path = f"{root}/{paquetes[0].numero_paquete}/ubicacion"
    for invalido in ({"latitud": 91, "longitud": 0}, {"latitud": 0, "longitud": -181}, {"latitud": 0}, {"latitud": "NaN", "longitud": 0}):
        assert (await client.patch(path, headers=headers, json=invalido)).status_code == 400
    await client.post(f"{BASE}/{recorrido['id']}/iniciar", headers=headers)
    assert (await client.patch(path, headers=headers, json=punto)).status_code == 400
    envio = await db_session.get(EnvioModel, paquetes[0].envio_id)
    assert envio.latitud_destino is None


@pytest.mark.asyncio
async def test_hu10_completar_ubicacion_requiere_logistica(
    client: AsyncClient, vendedor_token: str, repartidor_token: str
):
    path = f"{BASE}/{uuid.uuid4()}/paquetes/PAQ-TEST/ubicacion"
    punto = {"latitud": -31.43, "longitud": -64.21}
    assert (await client.patch(path, json=punto)).status_code == 401
    for token in (vendedor_token, repartidor_token):
        assert (await client.patch(path, headers={"Authorization": f"Bearer {token}"}, json=punto)).status_code == 403
