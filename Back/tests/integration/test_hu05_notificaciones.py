import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.constants.estados_logistica import (
    CanalNotificacionEnum,
    DestinatarioNotificacionEnum,
    EstadoNotificacionEnum,
)
from app.infrastructure.db.models import NotificacionEnvioModel
from app.infrastructure.email.email_provider import (
    MockEmailProvider,
    establecer_proveedor_email_personalizado,
)
from app.infrastructure.whatsapp.whatsapp_provider import MockWhatsAppProvider


def _payload_envio_notificacion():
    return {
        "remitente_nombre": "Carlos Gómez",
        "remitente_documento": "28111222",
        "remitente_telefono": "+543564112233",
        "remitente_email": "carlos.gomez@empresa.com",
        "destinatario_nombre": "Lucía Morales",
        "destinatario_telefono": "03564 15 445566",
        "destinatario_email": "lucia.morales@gmail.com",
        "tipo_entrega": "domicilio",
        "provincia_destino": "Córdoba",
        "ciudad_destino": "Córdoba",
        "direccion_destino": "Av. Vélez Sarsfield 500",
        "latitud_destino": -31.4201,
        "longitud_destino": -64.1888,
        "sucursal_origen_id": 1, "terminos_aceptados": True,
        "paquetes": [
            {
                "descripcion": "Notebook y accesorios",
                "peso_kg": 3.0,
                "largo_cm": 40.0,
                "ancho_cm": 30.0,
                "alto_cm": 15.0,
                "observaciones": "Frágil",
            }
        ],
    }


async def _logs(db: AsyncSession) -> list[NotificacionEnvioModel]:
    resultado = await db.execute(
        select(NotificacionEnvioModel)
        .order_by(NotificacionEnvioModel.created_at.asc())
        .execution_options(populate_existing=True)
    )
    return list(resultado.scalars().all())


@pytest.mark.asyncio
async def test_hu05_despacho_por_email_y_whatsapp_a_ambas_partes(
    client: AsyncClient, db_session: AsyncSession, whatsapp: MockWhatsAppProvider
):
    """HU05 E1: al crear el envío se comparte el token por email y WhatsApp con remitente y destinatario."""
    correo = MockEmailProvider()
    establecer_proveedor_email_personalizado(correo)

    resp = await client.post("/api/v1/envios", json=_payload_envio_notificacion())
    assert resp.status_code == 201
    token = resp.json()["data"]["token_seguimiento"]
    assert token.startswith("ENV-")

    assert {m["destinatario"] for m in correo.mensajes_enviados} == {
        "carlos.gomez@empresa.com",
        "lucia.morales@gmail.com",
    }
    for msg in correo.mensajes_enviados:
        assert token in msg["asunto"] and token in msg["cuerpo_texto"]
        assert f"/seguimiento?token={token}" in msg["cuerpo_texto"]
        assert "28111222" not in msg["cuerpo_texto"]  # sin documentos

    # Teléfonos normalizados a E.164 de celular argentino, incluido el formato local con 0 y 15.
    assert {m["destinatario"] for m in whatsapp.mensajes_enviados} == {"5493564112233", "5493564445566"}
    for msg in whatsapp.mensajes_enviados:
        assert token in msg["texto"] and f"/seguimiento?token={token}" in msg["texto"]
        assert msg["parametros"][1] == token

    logs = await _logs(db_session)
    assert len(logs) == 4
    assert {(log.canal, log.destinatario_tipo) for log in logs} == {
        (canal.value, tipo.value) for canal in CanalNotificacionEnum for tipo in DestinatarioNotificacionEnum
    }
    for log in logs:
        assert log.estado == EstadoNotificacionEnum.ENVIADO.value
        assert log.proveedor_mensaje_id is not None
        assert log.error_detalle is None
        assert log.procesando_at is None


@pytest.mark.asyncio
async def test_hu05_fallo_en_proveedor_no_bloquea_creacion_de_envio(client: AsyncClient, db_session: AsyncSession):
    """HU05: si el correo falla, el envío se crea igual y el fallo se audita por destinatario."""
    establecer_proveedor_email_personalizado(MockEmailProvider(forzar_error=True, mensaje_error="Servidor SMTP no responde"))

    resp = await client.post("/api/v1/envios", json=_payload_envio_notificacion())
    assert resp.status_code == 201

    logs = await _logs(db_session)
    emails = [log for log in logs if log.canal == CanalNotificacionEnum.EMAIL.value]
    whatsapps = [log for log in logs if log.canal == CanalNotificacionEnum.WHATSAPP.value]
    assert len(emails) == 2 and len(whatsapps) == 2
    for log in emails:
        assert log.estado == EstadoNotificacionEnum.FALLIDO.value
        assert "Servidor SMTP no responde" in (log.error_detalle or "")
    # Fallo parcial: el otro canal no se ve afectado.
    assert all(log.estado == EstadoNotificacionEnum.ENVIADO.value for log in whatsapps)


@pytest.mark.asyncio
async def test_hu05_excepcion_del_proveedor_no_expone_credenciales(
    client: AsyncClient, db_session: AsyncSession, whatsapp: MockWhatsAppProvider, monkeypatch
):
    establecer_proveedor_email_personalizado(MockEmailProvider())

    async def explotar(*args, **kwargs):
        raise RuntimeError("token=EAAG-secreto")

    monkeypatch.setattr(whatsapp, "enviar_whatsapp", explotar)
    resp = await client.post("/api/v1/envios", json=_payload_envio_notificacion())
    assert resp.status_code == 201
    whatsapps = [log for log in await _logs(db_session) if log.canal == CanalNotificacionEnum.WHATSAPP.value]
    assert len(whatsapps) == 2
    for log in whatsapps:
        assert log.estado == EstadoNotificacionEnum.FALLIDO.value
        assert "secreto" not in (log.error_detalle or "")


@pytest.mark.asyncio
async def test_hu05_telefono_invalido_falla_solo_whatsapp(
    client: AsyncClient, db_session: AsyncSession, whatsapp: MockWhatsAppProvider
):
    establecer_proveedor_email_personalizado(MockEmailProvider())
    payload = _payload_envio_notificacion()
    payload["destinatario_telefono"] = "123-456"
    assert (await client.post("/api/v1/envios", json=payload)).status_code == 201

    logs = await _logs(db_session)
    fallido = next(
        log for log in logs
        if log.canal == CanalNotificacionEnum.WHATSAPP.value
        and log.destinatario_tipo == DestinatarioNotificacionEnum.DESTINATARIO.value
    )
    assert fallido.estado == EstadoNotificacionEnum.FALLIDO.value
    assert "WhatsApp" in fallido.error_detalle
    assert len(whatsapp.mensajes_enviados) == 1
    assert sum(log.estado == EstadoNotificacionEnum.ENVIADO.value for log in logs) == 3


@pytest.mark.asyncio
async def test_hu05_consulta_y_reintento_solo_reenvian_lo_fallido(
    client: AsyncClient,
    db_session: AsyncSession,
    vendedor_token: str,
    whatsapp: MockWhatsAppProvider,
):
    """El personal ve el resultado por canal y reintenta sin duplicar los mensajes ya enviados."""
    establecer_proveedor_email_personalizado(MockEmailProvider(forzar_error=True))
    token = (await client.post("/api/v1/envios", json=_payload_envio_notificacion())).json()["data"][
        "token_seguimiento"
    ]
    headers = {"Authorization": f"Bearer {vendedor_token}"}

    consulta = await client.get(f"/api/v1/envios/{token.lower()}/notificaciones", headers=headers)
    assert consulta.status_code == 200, consulta.text
    items = consulta.json()["data"]["notificaciones"]
    assert len(items) == 4
    assert {i["estado"] for i in items if i["canal"] == "EMAIL"} == {"FALLIDO"}
    assert {i["estado"] for i in items if i["canal"] == "WHATSAPP"} == {"ENVIADO"}
    assert all(i["motivo"] == "NUEVO_ENVIO" for i in items)

    correo_ok = MockEmailProvider()
    establecer_proveedor_email_personalizado(correo_ok)
    reintento = await client.post(f"/api/v1/envios/{token}/notificaciones/reintentar", headers=headers)
    assert reintento.status_code == 200, reintento.text
    assert {i["estado"] for i in reintento.json()["data"]["notificaciones"]} == {"ENVIADO"}
    assert len(correo_ok.mensajes_enviados) == 2
    assert len(whatsapp.mensajes_enviados) == 2  # los WhatsApp ya enviados no se repiten

    # Un segundo reintento no envía nada nuevo ni crea filas.
    await client.post(f"/api/v1/envios/{token}/notificaciones/reintentar", headers=headers)
    assert len(correo_ok.mensajes_enviados) == 2
    assert len(await _logs(db_session)) == 4


@pytest.mark.asyncio
async def test_hu05_consulta_de_notificaciones_requiere_personal_autorizado(
    client: AsyncClient, repartidor_token: str, vendedor_token: str
):
    establecer_proveedor_email_personalizado(MockEmailProvider())
    token = (await client.post("/api/v1/envios", json=_payload_envio_notificacion())).json()["data"][
        "token_seguimiento"
    ]
    url = f"/api/v1/envios/{token}/notificaciones"
    assert (await client.get(url)).status_code == 401
    assert (await client.get(url, headers={"Authorization": f"Bearer {repartidor_token}"})).status_code == 403
    inexistente = await client.get(
        "/api/v1/envios/ENV-ZZZZZZZZZZ/notificaciones", headers={"Authorization": f"Bearer {vendedor_token}"}
    )
    assert inexistente.status_code == 404
