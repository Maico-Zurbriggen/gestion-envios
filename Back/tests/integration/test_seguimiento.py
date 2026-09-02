import pytest
from httpx import AsyncClient

from app.domain.constants.error_codes import ErrorCodes


def _paquete(**overrides):
    base = {
        "descripcion": "Ropa y calzado",
        "peso_kg": 3.5,
        "largo_cm": 40,
        "ancho_cm": 30,
        "alto_cm": 20,
        "observaciones": "Frágil",
    }
    base.update(overrides)
    return base


def _payload_domicilio(**overrides):
    base = {
        "remitente_nombre": "Juan Pérez",
        "remitente_documento": "30111222",
        "remitente_telefono": "+543564111111",
        "remitente_email": "juan.perez@example.com",
        "destinatario_nombre": "María Gómez",
        "destinatario_telefono": "+543564222222",
        "destinatario_email": "maria.gomez@example.com",
        "tipo_entrega": "domicilio",
        "provincia_destino": "Buenos Aires",
        "ciudad_destino": "La Plata",
        "direccion_destino": "Calle 50 N° 1234",
        "latitud_destino": -34.9214,
        "longitud_destino": -57.9544,
        "terminos_aceptados": True,
        "paquetes": [_paquete()],
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_hu04_escenario_1_consulta_publica_con_token_valido(client: AsyncClient):
    """HU04 - Escenario 1: consulta pública sin autenticación con token válido."""
    registro = await client.post("/api/v1/envios", json=_payload_domicilio())
    token = registro.json()["data"]["token_seguimiento"]

    resp = await client.get(f"/api/v1/seguimiento/{token}")
    assert resp.status_code == 200
    body = resp.json()
    seguimiento = body["data"]
    assert seguimiento["token_seguimiento"] == token
    assert "La Plata" in seguimiento["destino"]
    assert seguimiento["latitud_destino"] == -34.9214
    assert seguimiento["longitud_destino"] == -57.9544
    assert len(seguimiento["paquetes"]) == 1
    paquete = seguimiento["paquetes"][0]
    for campo in ("numero_paquete", "estado", "descripcion", "observaciones", "fecha_registro", "ultima_actualizacion"):
        assert campo in paquete

    # No debe exponer datos de contacto de remitente/destinatario (fuera del alcance de HU04).
    assert "remitente_documento" not in seguimiento
    assert "remitente_telefono" not in seguimiento
    assert "destinatario_telefono" not in seguimiento
    assert "remitente_email" not in seguimiento
    assert "destinatario_email" not in seguimiento


@pytest.mark.asyncio
async def test_hu04_domicilio_sin_ubicacion_marcada_devuelve_coordenadas_nulas(client: AsyncClient):
    """Si el remitente no marcó un punto en el mapa al registrar el envío a
    domicilio, el seguimiento debe devolver latitud/longitud en None en vez
    de inventar una ubicación."""
    payload = _payload_domicilio(latitud_destino=None, longitud_destino=None)
    registro = await client.post("/api/v1/envios", json=payload)
    token = registro.json()["data"]["token_seguimiento"]

    resp = await client.get(f"/api/v1/seguimiento/{token}")
    assert resp.status_code == 200
    seguimiento = resp.json()["data"]
    assert seguimiento["latitud_destino"] is None
    assert seguimiento["longitud_destino"] is None


@pytest.mark.asyncio
async def test_hu04_escenario_2_token_con_multiples_paquetes(client: AsyncClient):
    """HU04 - Escenario 2: un mismo token muestra todos los paquetes asociados."""
    payload = _payload_domicilio(paquetes=[_paquete(descripcion="Caja 1"), _paquete(descripcion="Caja 2")])
    registro = await client.post("/api/v1/envios", json=payload)
    token = registro.json()["data"]["token_seguimiento"]

    resp = await client.get(f"/api/v1/seguimiento/{token}")
    assert resp.status_code == 200
    paquetes = resp.json()["data"]["paquetes"]
    assert len(paquetes) == 2
    descripciones = {p["descripcion"] for p in paquetes}
    assert descripciones == {"Caja 1", "Caja 2"}


@pytest.mark.asyncio
async def test_hu04_escenario_3_token_inexistente(client: AsyncClient):
    """HU04 - Escenario 3: token inexistente devuelve error descriptivo, sin datos de envío."""
    resp = await client.get("/api/v1/seguimiento/ENV-NOEXISTE1")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == ErrorCodes.NOT_FOUND
    assert "data" not in body


@pytest.mark.asyncio
async def test_hu04_escenario_4_misma_vista_para_cualquiera_con_el_token(client: AsyncClient):
    """HU04 - Escenario 4: no hay diferenciación de rol; cualquiera con el token ve la misma info."""
    registro = await client.post("/api/v1/envios", json=_payload_domicilio())
    token = registro.json()["data"]["token_seguimiento"]

    resp_a = await client.get(f"/api/v1/seguimiento/{token}")
    resp_b = await client.get(f"/api/v1/seguimiento/{token}")
    assert resp_a.json()["data"] == resp_b.json()["data"]


@pytest.mark.asyncio
async def test_hu04_seguimiento_a_sucursal_muestra_nombre_y_direccion(client: AsyncClient):
    payload = _payload_domicilio(
        tipo_entrega="sucursal",
        provincia_destino=None,
        ciudad_destino=None,
        direccion_destino=None,
        sucursal_destino_id=2,
    )
    registro = await client.post("/api/v1/envios", json=payload)
    token = registro.json()["data"]["token_seguimiento"]

    resp = await client.get(f"/api/v1/seguimiento/{token}")
    seguimiento = resp.json()["data"]
    assert "Sucursal Test Norte" in seguimiento["destino"]
    assert seguimiento["latitud_destino"] == -32.95
    assert seguimiento["longitud_destino"] == -60.69
