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
    obtener_proveedor_email,
)


def _payload_envio_notificacion():
    return {
        "remitente_nombre": "Carlos Gómez",
        "remitente_documento": "28111222",
        "remitente_telefono": "+543564112233",
        "remitente_email": "carlos.gomez@empresa.com",
        "destinatario_nombre": "Lucía Morales",
        "destinatario_telefono": "+543564445566",
        "destinatario_email": "lucia.morales@gmail.com",
        "tipo_entrega": "domicilio",
        "provincia_destino": "Córdoba",
        "ciudad_destino": "Córdoba",
        "direccion_destino": "Av. Vélez Sarsfield 500",
        "latitud_destino": -31.4201,
        "longitud_destino": -64.1888,
        "terminos_aceptados": True,
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


@pytest.mark.asyncio
async def test_hu05_despacho_notificaciones_al_crear_envio(client: AsyncClient, db_session: AsyncSession):
    """HU05: Al crear un envío exitosamente, se despachan notificaciones por correo a emisor y destinatario."""
    mock_provider = MockEmailProvider()
    establecer_proveedor_email_personalizado(mock_provider)

    payload = _payload_envio_notificacion()
    resp = await client.post("/api/v1/envios", json=payload)
    assert resp.status_code == 201

    data = resp.json()["data"]
    token = data["token_seguimiento"]
    assert token.startswith("ENV-")

    # Verificar que el proveedor mock recibió los dos correos
    assert len(mock_provider.mensajes_enviados) == 2
    destinatarios = [m["destinatario"] for m in mock_provider.mensajes_enviados]
    assert "carlos.gomez@empresa.com" in destinatarios
    assert "lucia.morales@gmail.com" in destinatarios

    for msg in mock_provider.mensajes_enviados:
        assert token in msg["asunto"] or token in msg["cuerpo_texto"]
        assert "/seguimiento?token=" in msg["cuerpo_texto"]

    # Verificar persistencia en base de datos
    stmt = select(NotificacionEnvioModel).order_by(NotificacionEnvioModel.created_at.asc())
    result = await db_session.execute(stmt)
    logs = list(result.scalars().all())

    assert len(logs) == 2
    tipos = {l.destinatario_tipo for l in logs}
    assert tipos == {
        DestinatarioNotificacionEnum.REMITENTE.value,
        DestinatarioNotificacionEnum.DESTINATARIO.value,
    }

    for log in logs:
        assert log.canal == CanalNotificacionEnum.EMAIL.value
        assert log.estado == EstadoNotificacionEnum.ENVIADO.value
        assert log.proveedor_mensaje_id is not None
        assert log.error_detalle is None


@pytest.mark.asyncio
async def test_hu05_fallo_en_proveedor_no_bloquea_creacion_de_envio(client: AsyncClient, db_session: AsyncSession):
    """HU05: Si el servicio externo de correo falla, el envío se crea con éxito y el fallo se audita."""
    mock_provider = MockEmailProvider(forzar_error=True, mensaje_error="Servidor SMTP no responde")
    establecer_proveedor_email_personalizado(mock_provider)

    payload = _payload_envio_notificacion()
    resp = await client.post("/api/v1/envios", json=payload)

    # La creación principal NO se debe caer ni responder 500
    assert resp.status_code == 201
    token = resp.json()["data"]["token_seguimiento"]
    assert token.startswith("ENV-")

    # En la base de datos se debe registrar el log con estado FALLIDO
    stmt = select(NotificacionEnvioModel).order_by(NotificacionEnvioModel.created_at.asc())
    result = await db_session.execute(stmt)
    logs = list(result.scalars().all())

    assert len(logs) == 2
    for log in logs:
        assert log.estado == EstadoNotificacionEnum.FALLIDO.value
        assert "Servidor SMTP no responde" in (log.error_detalle or "")
