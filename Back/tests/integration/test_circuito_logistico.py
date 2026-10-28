"""Circuito completo: admisión, plazos, tope de visitas, retiro y devolución al remitente."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update

from app.infrastructure.db.models import NotificacionEnvioModel, PaqueteModel
from app.infrastructure.email.email_provider import MockEmailProvider, establecer_proveedor_email_personalizado
from tests.integration.test_hu10_recorridos import CORDOBA, _crear_paquete, _crear_repartidor, _generar
from tests.integration.test_hu11_hu12_reparto import BASE as REPARTO
from tests.integration.test_hu11_hu12_reparto import _headers

pytestmark = pytest.mark.asyncio


@pytest.fixture
def correo():
    proveedor = MockEmailProvider()
    establecer_proveedor_email_personalizado(proveedor)
    yield proveedor
    establecer_proveedor_email_personalizado(MockEmailProvider())


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _asuntos(correo: MockEmailProvider, destinatario: str) -> list[str]:
    return [m["asunto"] for m in correo.mensajes_enviados if m["destinatario"] == destinatario]


def _envio(paquetes: int = 1) -> dict:
    return {
        "remitente_nombre": "Carlos Gómez", "remitente_documento": "28111222", "remitente_telefono": "03564-15112233",
        "remitente_email": "remitente@empresa.com", "destinatario_nombre": "Lucía Morales",
        "destinatario_telefono": "+543564445566", "destinatario_email": "destinataria@gmail.com",
        "tipo_entrega": "sucursal", "sucursal_destino_id": 2, "terminos_aceptados": True,
        "paquetes": [
            {"descripcion": f"Caja {n + 1}", "peso_kg": 2, "largo_cm": 30, "ancho_cm": 20, "alto_cm": 10}
            for n in range(paquetes)
        ],
    }


def _retiro(documento: str = "28111222") -> dict:
    return {
        "tipo_retiro": "TITULAR",
        "documento_presentado": {"tipo": "DNI", "numero": documento},
        "destinatario_mayor_16": True,
        "sucursal_id": 1,
        "receptor_fecha_nacimiento": "1990-05-10",
        "documento_original_verificado": True,
    }


async def test_admision_registra_origen_balanza_bulto_y_avisa(client: AsyncClient, administrativo_token: str, correo):
    creado = (await client.post("/api/v1/envios", json=_envio(paquetes=2))).json()["data"]
    numero = creado["paquetes"][1]["numero_paquete"]
    assert "10 días" in next(m["cuerpo_texto"] for m in correo.mensajes_enviados if m["destinatario"] == "remitente@empresa.com")

    escaneo = (await client.get(f"/api/v1/terminal/paquetes/{numero}/escanear", headers=_auth(administrativo_token))).json()["data"]
    assert (escaneo["bulto"], escaneo["total_bultos"]) == (2, 2), "la etiqueta dice «2 de 2»"

    recepcion = await client.post(
        f"/api/v1/terminal/paquetes/{numero}/recepcionar",
        headers=_auth(administrativo_token),
        json={"sucursal_id": 1, "peso_balanza_kg": 3},
    )
    assert recepcion.status_code == 200, recepcion.text
    data = recepcion.json()["data"]
    assert data["peso_balanza_kg"] == 3 and "50 % más" in data["aviso_peso"]
    assert any(asunto == f"Recibimos tu paquete {numero}" for asunto in _asuntos(correo, "remitente@empresa.com"))

    # El otro bulto del mismo envío no genera un segundo aviso: se avisa por envío.
    otro = creado["paquetes"][0]["numero_paquete"]
    segunda = await client.post(
        f"/api/v1/terminal/paquetes/{otro}/recepcionar", headers=_auth(administrativo_token), json={"sucursal_id": 1}
    )
    assert segunda.status_code == 200, segunda.text
    recibidos = [a for a in _asuntos(correo, "remitente@empresa.com") if a.startswith("Recibimos tu paquete")]
    assert len(recibidos) == 1

    traza = (await client.get(f"/api/v1/admin/monitor/paquetes/{numero}", headers=_auth(administrativo_token))).json()["data"]
    assert traza["sucursal_origen"] and traza["peso_admision_kg"] == 3
    assert any(n["motivo"] == "Paquete recibido" for n in traza["notificaciones"])


async def test_registro_vencido_se_da_de_baja_y_no_se_admite(
    client: AsyncClient, db_session, administrativo_token: str, correo
):
    creado = (await client.post("/api/v1/envios", json=_envio())).json()["data"]
    numero = creado["paquetes"][0]["numero_paquete"]
    paquete = (await db_session.scalars(select(PaqueteModel).where(PaqueteModel.numero_paquete == numero))).one()
    paquete.created_at = datetime.now(UTC) - timedelta(days=11)
    await db_session.commit()

    vencido = await client.post(
        f"/api/v1/terminal/paquetes/{numero}/recepcionar", headers=_auth(administrativo_token), json={"sucursal_id": 1}
    )
    assert vencido.status_code == 400 and "venció" in vencido.json()["message"]

    plazos = (await client.post("/api/v1/admin/monitor/procesar-plazos", headers=_auth(administrativo_token))).json()["data"]
    assert plazos["registros_vencidos"] == 1
    await db_session.refresh(paquete)
    assert paquete.estado == "VENCIDO"
    assert any(asunto.startswith("Venció el registro") for asunto in _asuntos(correo, "remitente@empresa.com"))
    publico = (await client.get(f"/api/v1/seguimiento/{creado['token_seguimiento']}")).json()["data"]["paquetes"][0]
    assert "venció" in publico["historial"][-1]["descripcion"]


async def test_dos_visitas_sin_exito_quedan_para_retirar_y_se_entrega_en_sucursal(
    client: AsyncClient, db_session, administrativo_token: str, correo
):
    db_session.autoflush = False
    repartidor = await _crear_repartidor(db_session, "Repartidor visitas")
    [paquete] = await _crear_paquete(db_session, latitud=CORDOBA[0] + 0.01, longitud=CORDOBA[1] + 0.01)
    headers = _headers(repartidor)

    for visita in (1, 2):
        if visita == 2:
            # La segunda salida es otro día: el aviso «sale a reparto» se vuelve a mandar.
            await db_session.execute(
                update(NotificacionEnvioModel)
                .where(NotificacionEnvioModel.tipo_aviso == "EN_REPARTO")
                .values(created_at=datetime.now(UTC) - timedelta(hours=13))
            )
            await db_session.commit()
        recorrido = (await _generar(client, administrativo_token))["data"]["recorridos"][0]
        detalle = (await client.post(f"{REPARTO}/{recorrido['id']}/iniciar", headers=headers)).json()["data"]
        assert detalle["paradas"][0]["paquetes"][0]["visitas_previas"] == visita - 1
        salidas = [a for a in _asuntos(correo, "destino@test.com") if a.startswith("Hoy entregamos tu paquete")]
        assert len(salidas) == visita, "cada salida a reparto se avisa una vez"
        resp = await client.post(
            f"{REPARTO}/{recorrido['id']}/paquetes/{paquete.numero_paquete}/visita-fallida",
            headers=headers,
            json={"operacion_id": str(uuid.uuid4()), "motivo_fallo": "Nadie en el domicilio"},
        )
        assert resp.status_code == 200, resp.text
        await db_session.refresh(paquete)
        assert paquete.sucursal_actual_id == 1, "la visita fallida vuelve a la sucursal con el vehículo"
        if visita == 1:
            assert paquete.estado == "ENTREGA_FALLIDA" and paquete.retiro_hasta is None

    assert paquete.estado == "LISTO_PARA_RETIRO" and paquete.retiro_hasta is not None
    ultimo = [m for m in correo.mensajes_enviados if m["asunto"].startswith("Aviso de visita")][-1]
    assert "2 visitas previstas" in ultimo["cuerpo_texto"]

    token = (await client.get(f"/api/v1/seguimiento/{paquete.envio.token_seguimiento}")).json()["data"]
    publico = token["paquetes"][0]
    assert publico["retiro"]["lo_retira"] == "destinatario" and publico["visitas_fallidas"] == 2

    validar = (await client.get(f"/api/v1/sucursal/paquetes/{paquete.numero_paquete}/validar-retiro", headers=_auth(administrativo_token))).json()["data"]
    assert validar["disponible_para_retiro"] is True and validar["sucursal_retiro"]["id"] == 1
    retiro = await client.post(
        f"/api/v1/sucursal/paquetes/{paquete.id}/registrar-retiro", headers=_auth(administrativo_token), json=_retiro("40123456")
    )
    assert retiro.status_code == 200, retiro.text
    assert retiro.json()["data"]["estado"] == "ENTREGADO_EN_SUCURSAL"
    assert any(a.startswith("Entregamos el paquete") for a in _asuntos(correo, "carlos@test.com"))


async def test_retiro_vencido_vuelve_al_remitente(client: AsyncClient, db_session, administrativo_token: str, correo):
    db_session.autoflush = False
    vencido = datetime.now(UTC) - timedelta(hours=1)
    [en_destino] = await _crear_paquete(
        db_session, tipo_entrega="sucursal", sucursal_destino_id=2, estado="LISTO_PARA_RETIRO", sucursal_actual_id=2
    )
    [en_origen] = await _crear_paquete(
        db_session, tipo_entrega="sucursal", sucursal_destino_id=1, estado="LISTO_PARA_RETIRO", sucursal_actual_id=1
    )
    for paquete in (en_destino, en_origen):
        paquete.sucursal_origen_id = 1
        paquete.retiro_hasta = vencido
    await db_session.commit()

    plazos = (await client.post("/api/v1/admin/monitor/procesar-plazos", headers=_auth(administrativo_token))).json()["data"]
    assert plazos["devoluciones_iniciadas"] == 2
    await db_session.refresh(en_destino)
    await db_session.refresh(en_origen)
    assert en_destino.estado == "EN_DEVOLUCION" and en_destino.en_devolucion
    assert en_origen.estado == "LISTO_PARA_RETIRO" and en_origen.en_devolucion
    assert any(a.endswith("vuelve a vos") for a in _asuntos(correo, "carlos@test.com"))
    assert any(a.startswith("Ya podés retirar el paquete devuelto") for a in _asuntos(correo, "carlos@test.com"))

    # El que quedó en destino viaja de vuelta en un recorrido de larga distancia.
    await _crear_repartidor(db_session, "Larga vuelta", sucursal_id=2, tipo="LARGA")
    generado = (await _generar(client, administrativo_token, sucursal_id=2, tipo_distancia="LARGA"))["data"]["recorridos"]
    parada = generado[0]["paradas"][0] if generado and "paradas" in generado[0] else None
    detalle = (await client.get(f"/api/v1/recorridos/{generado[0]['id']}", headers=_auth(administrativo_token))).json()["data"]
    parada = detalle["paradas"][0]
    assert parada["sucursal_destino"]["id"] == 1 and parada["paquetes"][0]["en_devolucion"] is True

    en_espera = (await client.get(
        "/api/v1/admin/monitor/paquetes", params={"grupo": "PARA_RETIRAR"}, headers=_auth(administrativo_token)
    )).json()["data"]
    assert en_origen.numero_paquete not in {p["numero_paquete"] for p in en_espera["paquetes"]}

    # El que ya está en origen lo retira el remitente con su DNI.
    validar = (await client.get(f"/api/v1/sucursal/paquetes/{en_origen.numero_paquete}/validar-retiro", headers=_auth(administrativo_token))).json()["data"]
    assert validar["es_devolucion"] is True and validar["datos_destinatario"]["nombre"] == "Carlos Remitente"
    retiro = await client.post(
        f"/api/v1/sucursal/paquetes/{en_origen.id}/registrar-retiro", headers=_auth(administrativo_token), json=_retiro()
    )
    assert retiro.status_code == 200, retiro.text
    assert retiro.json()["data"]["estado"] == "DEVUELTO"
    resumen = (await client.get("/api/v1/admin/monitor/resumen", headers=_auth(administrativo_token))).json()["data"]
    assert resumen["por_grupo"]["DEVOLUCIONES"] == 2
    assert resumen["por_grupo"]["PARA_RETIRAR"] == 0
    listado = (await client.get(
        "/api/v1/admin/monitor/paquetes", params={"grupo": "DEVOLUCIONES"}, headers=_auth(administrativo_token)
    )).json()["data"]
    assert {p["grupo"] for p in listado["paquetes"]} == {"DEVOLUCIONES"} and listado["total"] == 2
