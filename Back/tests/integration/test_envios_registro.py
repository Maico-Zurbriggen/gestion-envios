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
async def test_hu03_escenario_1_registro_domicilio_exitoso_sin_autenticacion(client: AsyncClient):
    """HU03 - Escenario 1: registro exitoso, sin header Authorization."""
    resp = await client.post("/api/v1/envios", json=_payload_domicilio())
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "success"
    envio = data["data"]
    assert envio["token_seguimiento"].startswith("ENV-")
    assert len(envio["paquetes"]) == 1
    paquete = envio["paquetes"][0]
    assert paquete["numero_paquete"].startswith("PAQ-")
    assert paquete["estado"] == "Pendiente"
    assert envio["direccion_destino"] == "Calle 50 N° 1234"
    assert envio["sucursal_destino"] is None


@pytest.mark.asyncio
async def test_hu03_escenario_1_registro_sucursal_con_multiples_paquetes(client: AsyncClient):
    """HU03 - Escenario 1 + HU04 Escenario 2: un mismo envío (token) puede tener varios paquetes."""
    payload = _payload_domicilio(
        tipo_entrega="sucursal",
        provincia_destino=None,
        ciudad_destino=None,
        direccion_destino=None,
        sucursal_destino_id=1,
        paquetes=[_paquete(descripcion="Caja 1"), _paquete(descripcion="Caja 2")],
    )
    resp = await client.post("/api/v1/envios", json=payload)
    assert resp.status_code == 201
    envio = resp.json()["data"]
    assert len(envio["paquetes"]) == 2
    numeros = {p["numero_paquete"] for p in envio["paquetes"]}
    assert len(numeros) == 2
    assert envio["sucursal_destino"]["id"] == 1
    assert envio["sucursal_destino"]["nombre"] == "Sucursal Test Centro"


@pytest.mark.asyncio
async def test_hu03_escenario_2_terminos_no_aceptados_es_rechazado(client: AsyncClient):
    resp = await client.post("/api/v1/envios", json=_payload_domicilio(terminos_aceptados=False))
    assert resp.status_code == 400
    assert resp.json()["code"] == ErrorCodes.VALIDATION_ERROR


@pytest.mark.asyncio
async def test_hu03_escenario_2_sucursal_invalida_es_rechazada(client: AsyncClient):
    payload = _payload_domicilio(
        tipo_entrega="sucursal",
        provincia_destino=None,
        ciudad_destino=None,
        direccion_destino=None,
        sucursal_destino_id=9999,
    )
    resp = await client.post("/api/v1/envios", json=payload)
    assert resp.status_code == 400
    assert resp.json()["code"] == ErrorCodes.VALIDATION_ERROR


@pytest.mark.asyncio
async def test_hu03_escenario_2_domicilio_incompleto_es_rechazado(client: AsyncClient):
    payload = _payload_domicilio(direccion_destino=None)
    resp = await client.post("/api/v1/envios", json=payload)
    assert resp.status_code == 400
    assert resp.json()["code"] == ErrorCodes.VALIDATION_ERROR


@pytest.mark.asyncio
async def test_hu03_escenario_2_paquete_supera_peso_maximo(client: AsyncClient):
    resp = await client.post("/api/v1/envios", json=_payload_domicilio(paquetes=[_paquete(peso_kg=30)]))
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == ErrorCodes.VALIDATION_ERROR
    assert any("peso_kg" in e["field"] for e in body["errors"])


@pytest.mark.asyncio
async def test_hu03_escenario_2_paquete_supera_dimension_individual_maxima(client: AsyncClient):
    resp = await client.post(
        "/api/v1/envios", json=_payload_domicilio(paquetes=[_paquete(largo_cm=200)])
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == ErrorCodes.VALIDATION_ERROR
    assert any("largo_cm" in e["field"] for e in body["errors"])


@pytest.mark.asyncio
async def test_hu03_escenario_2_suma_de_dimensiones_supera_el_maximo(client: AsyncClient):
    payload = _payload_domicilio(
        paquetes=[_paquete(largo_cm=100, ancho_cm=100, alto_cm=100)]
    )
    resp = await client.post("/api/v1/envios", json=payload)
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == ErrorCodes.VALIDATION_ERROR
    assert any("dimensiones" in e["field"] for e in body["errors"])
