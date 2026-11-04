"""Tests de integración de HU08 — Sección de preguntas frecuentes.

> Yo como usuario público deseo consultar una sección de preguntas frecuentes,
> para resolver dudas habituales sin iniciar sesión ni contactar a un operador.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.constants.error_codes import ErrorCodes
from app.domain.constants.scopes import ScopeEnum
from app.domain.rules.paquete_rules import PESO_MAX_KG
from app.infrastructure.auth.jwt_handler import ManejadorJWT
from app.infrastructure.db.models import PreguntaFrecuenteModel
from app.infrastructure.db.seed import (
    PREGUNTAS_FRECUENTES_BASE,
    RESPUESTAS_ANTERIORES,
    sembrar_preguntas_frecuentes,
)

PUBLICO = "/api/v1/preguntas-frecuentes"
ADMIN = "/api/v1/admin/preguntas-frecuentes"


async def _cargar_preguntas(db: AsyncSession) -> list[PreguntaFrecuenteModel]:
    preguntas = [
        PreguntaFrecuenteModel(
            categoria="Envíos",
            pregunta="¿Cómo registro un envío?",
            respuesta="Desde el formulario público de registro.",
            orden=10,
            publicada=True,
        ),
        PreguntaFrecuenteModel(
            categoria="Retiro en sucursal",
            pregunta="¿Qué necesito para retirar?",
            respuesta="Presentar el documento de identidad original.",
            orden=20,
            publicada=True,
        ),
        PreguntaFrecuenteModel(
            categoria=None,
            pregunta="¿Tienen atención telefónica?",
            respuesta="Sí, de lunes a viernes de 9 a 18 horas.",
            orden=30,
            publicada=True,
        ),
        PreguntaFrecuenteModel(
            categoria="Envíos",
            pregunta="Borrador sin publicar",
            respuesta="Este contenido todavía no se muestra.",
            orden=5,
            publicada=False,
        ),
    ]
    db.add_all(preguntas)
    await db.commit()
    for p in preguntas:
        await db.refresh(p)
    return preguntas


# --- Escenario 1: consulta pública sin iniciar sesión ---


@pytest.mark.asyncio
async def test_hu08_escenario_1_consulta_publica_sin_iniciar_sesion(client: AsyncClient, db_session: AsyncSession):
    """HU08 Escenario 1: el sistema muestra el contenido sin exigir inicio de sesión."""
    await _cargar_preguntas(db_session)

    resp = await client.get(PUBLICO)

    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["status"] == "success"
    data = cuerpo["data"]
    assert data["total"] == 3
    assert [p["pregunta"] for p in data["preguntas"]] == [
        "¿Cómo registro un envío?",
        "¿Qué necesito para retirar?",
        "¿Tienen atención telefónica?",
    ]
    # La pregunta sin categoría se agrupa en "General"
    assert data["preguntas"][2]["categoria"] == "General"
    assert data["categorias"] == [
        {"nombre": "Envíos", "cantidad": 1},
        {"nombre": "Retiro en sucursal", "cantidad": 1},
        {"nombre": "General", "cantidad": 1},
    ]


@pytest.mark.asyncio
async def test_hu08_no_muestra_preguntas_sin_publicar(client: AsyncClient, db_session: AsyncSession):
    await _cargar_preguntas(db_session)

    resp = await client.get(PUBLICO)

    preguntas = [p["pregunta"] for p in resp.json()["data"]["preguntas"]]
    assert "Borrador sin publicar" not in preguntas


@pytest.mark.asyncio
async def test_hu08_filtra_por_categoria_sin_distinguir_tildes(client: AsyncClient, db_session: AsyncSession):
    await _cargar_preguntas(db_session)

    resp = await client.get(PUBLICO, params={"categoria": "envios"})

    data = resp.json()["data"]
    assert data["total"] == 1
    assert data["preguntas"][0]["pregunta"] == "¿Cómo registro un envío?"
    # Las categorías se listan completas aunque se haya filtrado
    assert len(data["categorias"]) == 3


@pytest.mark.asyncio
async def test_hu08_busqueda_libre(client: AsyncClient, db_session: AsyncSession):
    await _cargar_preguntas(db_session)

    resp = await client.get(PUBLICO, params={"q": "DOCUMENTO retirar"})
    data = resp.json()["data"]
    assert data["total"] == 1
    assert data["preguntas"][0]["pregunta"] == "¿Qué necesito para retirar?"

    sin_resultados = await client.get(PUBLICO, params={"q": "criptomonedas"})
    assert sin_resultados.status_code == 200
    assert sin_resultados.json()["data"]["total"] == 0
    assert sin_resultados.json()["data"]["preguntas"] == []


@pytest.mark.asyncio
async def test_hu08_seccion_vacia_responde_200(client: AsyncClient):
    resp = await client.get(PUBLICO)

    assert resp.status_code == 200
    assert resp.json()["data"] == {"total": 0, "categorias": [], "preguntas": []}


# --- Contenido inicial sembrado ---


@pytest.mark.asyncio
async def test_hu08_siembra_inicial_es_idempotente_y_respeta_lo_editado(
    client: AsyncClient, db_session: AsyncSession
):
    await sembrar_preguntas_frecuentes(db_session)
    total = (await db_session.execute(select(func.count(PreguntaFrecuenteModel.id)))).scalar_one()
    assert total == len(PREGUNTAS_FRECUENTES_BASE)

    # Un administrador borra una pregunta: la siembra no la vuelve a crear
    primera = (await db_session.execute(select(PreguntaFrecuenteModel).limit(1))).scalar_one()
    await db_session.delete(primera)
    await db_session.commit()
    await sembrar_preguntas_frecuentes(db_session)
    total_despues = (await db_session.execute(select(func.count(PreguntaFrecuenteModel.id)))).scalar_one()
    assert total_despues == len(PREGUNTAS_FRECUENTES_BASE) - 1


@pytest.mark.asyncio
async def test_hu08_actualiza_solo_las_respuestas_viejas_sin_editar(client: AsyncClient, db_session: AsyncSession):
    """Una base sembrada antes del circuito nuevo recibe los textos actuales,
    salvo las respuestas que un administrador ya cambió."""
    base = {datos["pregunta"]: datos for datos in PREGUNTAS_FRECUENTES_BASE}
    preguntas = list(RESPUESTAS_ANTERIORES)
    sin_editar, editada = preguntas[0], preguntas[1]
    db_session.add(PreguntaFrecuenteModel(**{**base[sin_editar], "respuesta": RESPUESTAS_ANTERIORES[sin_editar]}, publicada=True))
    db_session.add(PreguntaFrecuenteModel(**{**base[editada], "respuesta": "Texto propio del administrador."}, publicada=True))
    await db_session.commit()

    await sembrar_preguntas_frecuentes(db_session)

    filas = {
        p.pregunta: p.respuesta
        for p in (await db_session.execute(select(PreguntaFrecuenteModel))).scalars()
    }
    assert filas[sin_editar] == base[sin_editar]["respuesta"]
    assert filas[editada] == "Texto propio del administrador."
    assert len(filas) == 2, "Con contenido cargado no se agregan preguntas"


@pytest.mark.asyncio
async def test_hu08_contenido_sembrado_refleja_las_reglas_reales(client: AsyncClient, db_session: AsyncSession):
    await sembrar_preguntas_frecuentes(db_session)

    resp = await client.get(PUBLICO, params={"q": "pesar"})

    data = resp.json()["data"]
    assert data["total"] >= 1
    assert f"{PESO_MAX_KG} kg" in data["preguntas"][0]["respuesta"]
    nombres = [c["nombre"] for c in data["categorias"]]
    assert {"Envíos", "Seguimiento", "Retiro en sucursal", "Reclamos"} <= set(nombres)


# --- Administración del contenido ---


@pytest.mark.asyncio
async def test_hu08_administracion_requiere_rol_administrativo(
    client: AsyncClient,
    vendedor_token: str,
    repartidor_token: str,
    administrativo_token: str,
):
    assert (await client.get(ADMIN)).status_code == 401

    for token in (vendedor_token, repartidor_token):
        resp = await client.get(ADMIN, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
        assert resp.json()["code"] == ErrorCodes.FORBIDDEN_ACCESS

    token_reset = ManejadorJWT.emitir_token(
        usuario_id=str(uuid.uuid4()), rol="ADMINISTRATIVO", scope=ScopeEnum.PASSWORD_RESET_ONLY.value
    )
    resp_reset = await client.get(ADMIN, headers={"Authorization": f"Bearer {token_reset}"})
    assert resp_reset.status_code == 403
    assert resp_reset.json()["code"] == ErrorCodes.FORBIDDEN_SCOPE

    resp_ok = await client.get(ADMIN, headers={"Authorization": f"Bearer {administrativo_token}"})
    assert resp_ok.status_code == 200


@pytest.mark.asyncio
async def test_hu08_administracion_lista_tambien_las_no_publicadas(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str
):
    await _cargar_preguntas(db_session)

    resp = await client.get(ADMIN, headers={"Authorization": f"Bearer {administrativo_token}"})

    data = resp.json()["data"]
    assert len(data) == 4
    borrador = next(p for p in data if p["pregunta"] == "Borrador sin publicar")
    assert borrador["publicada"] is False


@pytest.mark.asyncio
async def test_hu08_alta_de_pregunta_se_ve_en_la_vista_publica(client: AsyncClient, administrativo_token: str):
    headers = {"Authorization": f"Bearer {administrativo_token}"}

    resp = await client.post(
        ADMIN,
        headers=headers,
        json={
            "categoria": "  Pagos  ",
            "pregunta": "¿Qué medios de pago aceptan?",
            "respuesta": "Efectivo y tarjetas de débito o crédito en sucursal.",
            "orden": 1,
        },
    )

    assert resp.status_code == 201
    creada = resp.json()["data"]
    assert creada["categoria"] == "Pagos"
    assert creada["publicada"] is True

    publica = await client.get(PUBLICO)
    assert publica.json()["data"]["preguntas"][0]["pregunta"] == "¿Qué medios de pago aceptan?"


@pytest.mark.asyncio
async def test_hu08_rechaza_pregunta_duplicada(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str
):
    await _cargar_preguntas(db_session)

    resp = await client.post(
        ADMIN,
        headers={"Authorization": f"Bearer {administrativo_token}"},
        json={"pregunta": "como registro un ENVIO", "respuesta": "Texto de una respuesta duplicada."},
    )

    assert resp.status_code == 409
    assert resp.json()["code"] == ErrorCodes.DUPLICATE_ENTRY
    assert resp.json()["errors"][0]["field"] == "pregunta"


@pytest.mark.asyncio
async def test_hu08_alta_con_datos_invalidos(client: AsyncClient, administrativo_token: str):
    resp = await client.post(
        ADMIN,
        headers={"Authorization": f"Bearer {administrativo_token}"},
        json={"pregunta": "¿?", "respuesta": "corta", "orden": -1},
    )

    assert resp.status_code == 400
    campos = {e["field"] for e in resp.json()["errors"]}
    assert {"pregunta", "respuesta", "orden"} <= campos


@pytest.mark.asyncio
async def test_hu08_modificacion_parcial_y_despublicacion(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str
):
    preguntas = await _cargar_preguntas(db_session)
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    objetivo = preguntas[0]

    resp = await client.patch(
        f"{ADMIN}/{objetivo.id}",
        headers=headers,
        json={"respuesta": "Desde el formulario público, sin crear una cuenta."},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["respuesta"] == "Desde el formulario público, sin crear una cuenta."
    # Los campos no enviados quedan igual
    assert data["categoria"] == "Envíos"
    assert data["pregunta"] == "¿Cómo registro un envío?"

    resp_ocultar = await client.patch(f"{ADMIN}/{objetivo.id}", headers=headers, json={"publicada": False})
    assert resp_ocultar.status_code == 200
    publica = await client.get(PUBLICO)
    assert "¿Cómo registro un envío?" not in [p["pregunta"] for p in publica.json()["data"]["preguntas"]]

    resp_sin_categoria = await client.patch(f"{ADMIN}/{objetivo.id}", headers=headers, json={"categoria": None})
    assert resp_sin_categoria.json()["data"]["categoria"] is None


@pytest.mark.asyncio
async def test_hu08_modificacion_valida_el_cuerpo(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str
):
    preguntas = await _cargar_preguntas(db_session)
    headers = {"Authorization": f"Bearer {administrativo_token}"}

    vacio = await client.patch(f"{ADMIN}/{preguntas[0].id}", headers=headers, json={})
    assert vacio.status_code == 400

    nulo = await client.patch(f"{ADMIN}/{preguntas[0].id}", headers=headers, json={"pregunta": None})
    assert nulo.status_code == 400

    duplicada = await client.patch(
        f"{ADMIN}/{preguntas[0].id}", headers=headers, json={"pregunta": "¿QUÉ NECESITO PARA RETIRAR?"}
    )
    assert duplicada.status_code == 409

    # Reescribir la propia pregunta con otro formato no es duplicado
    misma = await client.patch(
        f"{ADMIN}/{preguntas[0].id}", headers=headers, json={"pregunta": "¿Cómo registro un envío?"}
    )
    assert misma.status_code == 200


@pytest.mark.asyncio
async def test_hu08_eliminacion_y_404(client: AsyncClient, db_session: AsyncSession, administrativo_token: str):
    preguntas = await _cargar_preguntas(db_session)
    headers = {"Authorization": f"Bearer {administrativo_token}"}

    resp = await client.delete(f"{ADMIN}/{preguntas[1].id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    assert (await client.get(f"{ADMIN}/{preguntas[1].id}", headers=headers)).status_code == 404
    assert (await client.delete(f"{ADMIN}/{preguntas[1].id}", headers=headers)).status_code == 404
    no_existe = await client.patch(f"{ADMIN}/99999", headers=headers, json={"orden": 1})
    assert no_existe.status_code == 404
    assert no_existe.json()["code"] == ErrorCodes.NOT_FOUND
