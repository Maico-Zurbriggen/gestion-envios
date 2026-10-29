"""Correos a clientes personalizables: plantillas, datos de la empresa, vista previa y prueba."""

import pytest
from httpx import AsyncClient

from app.infrastructure.email.email_provider import MockEmailProvider, establecer_proveedor_email_personalizado

API = "/api/v1/admin/correos"


@pytest.fixture
def correo():
    proveedor = MockEmailProvider()
    establecer_proveedor_email_personalizado(proveedor)
    yield proveedor
    establecer_proveedor_email_personalizado(MockEmailProvider())


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _payload_envio() -> dict:
    return {
        "remitente_nombre": "Carlos Gómez", "remitente_documento": "28111222", "remitente_telefono": "03564-15112233",
        "remitente_email": "carlos.gomez@empresa.com", "destinatario_nombre": "Lucía Morales", "destinatario_telefono": "+543564445566",
        "destinatario_email": "lucia.morales@gmail.com", "tipo_entrega": "sucursal", "sucursal_destino_id": 2, "sucursal_origen_id": 1, "terminos_aceptados": True,
        "paquetes": [{"descripcion": "Libros", "peso_kg": 2, "largo_cm": 30, "ancho_cm": 20, "alto_cm": 10}],
    }


@pytest.mark.asyncio
async def test_listado_trae_las_plantillas_de_fabrica(client: AsyncClient, administrativo_token: str):
    resp = await client.get(f"{API}/plantillas", headers=_auth(administrativo_token))
    assert resp.status_code == 200
    data = resp.json()["data"]
    claves = [p["clave"] for p in data["plantillas"]]
    assert claves == [
        "NUEVO_ENVIO_REMITENTE", "NUEVO_ENVIO_DESTINATARIO", "ADMITIDO", "EN_REPARTO", "VISITA_FALLIDA",
        "LISTO_PARA_RETIRO", "ENTREGADO", "DEVOLUCION", "DEVOLUCION_LISTA", "VENCIDO",
    ], "una plantilla por cada aviso del circuito, en orden de ocurrencia"
    assert not any(p["personalizada"] for p in data["plantillas"])
    assert data["configuracion"]["nombre_marca"] == "Gestión de Envíos"
    assert {"nombre", "token", "enlace"} <= {v["nombre"] for v in data["plantillas"][0]["variables"]}


@pytest.mark.asyncio
async def test_guardar_valida_variables_y_se_usa_en_los_envios(
    client: AsyncClient, administrativo_token: str, correo: MockEmailProvider
):
    textos = {
        "asunto": "Recibimos tu envío {token}",
        "titulo": "¡Gracias, {nombre}!",
        "mensaje": "Tu paquete para {destinatario} ya está en camino.\n\nCualquier duda, escribinos.",
        "texto_boton": "Seguir mi envío",
        "pie": "Atención al cliente de {marca}.",
    }
    malo = await client.put(f"{API}/plantillas/NUEVO_ENVIO_REMITENTE", json={**textos, "titulo": "Hola {apellido}"}, headers=_auth(administrativo_token))
    assert malo.status_code == 400
    assert malo.json()["errors"][0]["field"] == "titulo"

    ok = await client.put(f"{API}/plantillas/NUEVO_ENVIO_REMITENTE", json=textos, headers=_auth(administrativo_token))
    assert ok.status_code == 200
    assert ok.json()["data"]["personalizada"] is True
    empresa = await client.put(f"{API}/configuracion", json={
        "nombre_marca": "Envíos del Centro", "firma": "Equipo de atención", "telefono_contacto": "0351 400-1234",
        "email_contacto": "hola@enviosdelcentro.com", "sitio_web": "https://enviosdelcentro.com", "mensaje_legal": "Mensaje automático.",
    }, headers=_auth(administrativo_token))
    assert empresa.status_code == 200

    resp = await client.post("/api/v1/envios", json=_payload_envio())
    token = resp.json()["data"]["token_seguimiento"]
    al_remitente = next(m for m in correo.mensajes_enviados if m["destinatario"] == "carlos.gomez@empresa.com")
    assert al_remitente["asunto"] == f"Recibimos tu envío {token}"
    assert "¡Gracias, Carlos Gómez!" in al_remitente["cuerpo_html"]
    assert "Envíos del Centro" in al_remitente["cuerpo_html"] and "0351 400-1234" in al_remitente["cuerpo_html"]
    assert "Lucía Morales" in al_remitente["cuerpo_texto"]
    al_destinatario = next(m for m in correo.mensajes_enviados if m["destinatario"] == "lucia.morales@gmail.com")
    assert al_destinatario["asunto"].startswith("Tenés un paquete en camino"), "las demás plantillas siguen de fábrica"

    restablecida = await client.delete(f"{API}/plantillas/NUEVO_ENVIO_REMITENTE", headers=_auth(administrativo_token))
    assert restablecida.json()["data"]["personalizada"] is False


@pytest.mark.asyncio
async def test_textos_editados_no_inyectan_html(client: AsyncClient, administrativo_token: str):
    resp = await client.post(
        f"{API}/plantillas/VISITA_FALLIDA/vista-previa",
        json={"titulo": "<script>alert(1)</script>", "mensaje": "Línea <b>uno</b>"},
        headers=_auth(administrativo_token),
    )
    assert resp.status_code == 200
    html = resp.json()["data"]["html"]
    assert "<script>" not in html and "&lt;script&gt;" in html and "&lt;b&gt;uno" in html


@pytest.mark.asyncio
async def test_vista_previa_y_prueba_sin_guardar(client: AsyncClient, administrativo_token: str, correo: MockEmailProvider):
    previa = await client.post(f"{API}/plantillas/NUEVO_ENVIO_DESTINATARIO/vista-previa", json={"titulo": "Título de prueba"}, headers=_auth(administrativo_token))
    data = previa.json()["data"]
    assert "Título de prueba" in data["html"] and "ENV-7K2Q9XWB4M" in data["html"] and "PAQ-4D8R2M7KQ1" in data["html"]

    prueba = await client.post(f"{API}/plantillas/NUEVO_ENVIO_DESTINATARIO/prueba", json={"email": "yo@empresa.com"}, headers=_auth(administrativo_token))
    assert prueba.status_code == 200 and prueba.json()["data"]["enviado"] is True
    assert correo.mensajes_enviados[-1]["destinatario"] == "yo@empresa.com"
    assert correo.mensajes_enviados[-1]["asunto"].startswith("[Prueba]")

    listado = await client.get(f"{API}/plantillas", headers=_auth(administrativo_token))
    assert not any(p["personalizada"] for p in listado.json()["data"]["plantillas"]), "la vista previa y la prueba no guardan"


@pytest.mark.asyncio
async def test_permisos_y_errores(client: AsyncClient, vendedor_token: str, administrativo_token: str):
    assert (await client.get(f"{API}/plantillas", headers=_auth(vendedor_token))).status_code == 403
    assert (await client.get(f"{API}/plantillas")).status_code == 401
    assert (await client.put(f"{API}/plantillas/NO_EXISTE", json={"asunto": "a", "titulo": "b", "mensaje": "c", "texto_boton": "d"}, headers=_auth(administrativo_token))).status_code == 404
    sitio = await client.put(f"{API}/configuracion", json={"nombre_marca": "X", "sitio_web": "enviosdelcentro.com"}, headers=_auth(administrativo_token))
    assert sitio.status_code == 400
