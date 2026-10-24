"""Flujo de punta a punta, solo por HTTP, de un envío a través de las historias implementadas.

HU03 registro -> HU06 recepción en terminal -> HU10 recorridos (perfil de
repartidor, generación, edición, alertas e inicio) -> HU04 seguimiento público
-> HU07 reclamo desde el token y su gestión -> HU08 preguntas frecuentes.

A diferencia de los tests por historia, acá ningún dato se precarga en la
base: todo se crea con los mismos endpoints que usa el frontend, así que el
test falla si dos historias dejan de encajar entre sí.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.constants.estados_logistica import EstadoPaqueteEnum, EstadoRecorridoEnum
from app.infrastructure.db.seed import sembrar_preguntas_frecuentes


def _envio_a_domicilio(direccion: str, latitud: float | None, longitud: float | None) -> dict:
    return {
        "remitente_nombre": "Juan Pérez",
        "remitente_documento": "30111222",
        "remitente_telefono": "+543564111111",
        "remitente_email": "juan.perez@example.com",
        "destinatario_nombre": "María Gómez",
        "destinatario_telefono": "+543564222222",
        "destinatario_email": "maria.gomez@example.com",
        "tipo_entrega": "domicilio",
        "provincia_destino": "Córdoba",
        "ciudad_destino": "Córdoba",
        "direccion_destino": direccion,
        "latitud_destino": latitud,
        "longitud_destino": longitud,
        "terminos_aceptados": True,
        "paquetes": [{"descripcion": "Libros", "peso_kg": 3, "largo_cm": 30, "ancho_cm": 20, "alto_cm": 15}],
    }


@pytest.mark.asyncio
async def test_flujo_completo_registro_recepcion_recorrido_seguimiento_y_reclamo(
    client: AsyncClient,
    db_session: AsyncSession,
    administrativo_token: str,
    vendedor_token: str,
    repartidor_usuario,
):
    admin = {"Authorization": f"Bearer {administrativo_token}"}
    vendedor = {"Authorization": f"Bearer {vendedor_token}"}

    # --- HU03: dos envíos a domicilio en Córdoba; uno sin marcar en el mapa ---
    con_mapa = (await client.post("/api/v1/envios", json=_envio_a_domicilio("San Martín 100", -31.41, -64.19))).json()
    sin_mapa = (await client.post("/api/v1/envios", json=_envio_a_domicilio("Colón 900", None, None))).json()
    token = con_mapa["data"]["token_seguimiento"]
    paquete = con_mapa["data"]["paquetes"][0]["numero_paquete"]
    paquete_sin_mapa = sin_mapa["data"]["paquetes"][0]["numero_paquete"]

    # --- HU06: el vendedor escanea y recibe ambos paquetes en la terminal de Córdoba ---
    for numero in (paquete, paquete_sin_mapa):
        escaneo = await client.get(f"/api/v1/terminal/paquetes/{numero.lower()}/escanear", headers=vendedor)
        assert escaneo.json()["data"]["disponible_para_recepcion"] is True
        recepcion = await client.post(
            f"/api/v1/terminal/paquetes/{numero}/recepcionar", headers=vendedor, json={"sucursal_id": 1}
        )
        assert recepcion.status_code == 200

    # --- HU10: se configura el repartidor y se generan los recorridos del día ---
    perfil = await client.put(
        f"/api/v1/repartidores/{repartidor_usuario.id}/perfil",
        headers=admin,
        json={"sucursal_base_id": 1, "tipo_reparto": "CORTA"},
    )
    assert perfil.json()["data"]["disponible_para_recorridos"] is True

    generacion = await client.post(
        "/api/v1/recorridos/generar", headers=admin, json={"sucursal_id": 1, "tipo_distancia": "CORTA"}
    )
    assert generacion.status_code == 200
    data = generacion.json()["data"]
    recorrido = data["recorridos"][0]
    assert recorrido["repartidor"]["usuario_id"] == str(repartidor_usuario.id)
    assert [p["numero_paquete"] for p in recorrido["paradas"][0]["paquetes"]] == [paquete]
    # El domicilio sin ubicación quedó afuera y se alertó (Escenario 3)
    assert [a["numero_paquete"] for a in data["alertas"]] == [paquete_sin_mapa]

    # Control manual: logística lo agrega igual al recorrido y la alerta se resuelve
    edicion = await client.put(
        f"/api/v1/recorridos/{recorrido['id']}/paquetes",
        headers=admin,
        json={"paquetes": [paquete, paquete_sin_mapa]},
    )
    assert edicion.json()["data"]["estado"] == EstadoRecorridoEnum.EN_EDICION.value
    assert edicion.json()["alertas"] == []
    pendientes = await client.get("/api/v1/recorridos/alertas", headers=admin, params={"sucursal_id": 1})
    assert pendientes.json()["total"] == 0

    inicio = await client.post(f"/api/v1/recorridos/{recorrido['id']}/iniciar", headers=admin)
    assert inicio.json()["data"]["estado"] == EstadoRecorridoEnum.EN_CURSO.value

    # --- HU04: el seguimiento público muestra que el paquete salió a reparto ---
    seguimiento = await client.get(f"/api/v1/seguimiento/{token}")
    assert seguimiento.json()["data"]["paquetes"][0]["estado"] == EstadoPaqueteEnum.EN_REPARTO.value

    # --- HU07: desde la vista del token se inicia un reclamo y logística lo resuelve ---
    habilitacion = await client.get(f"/api/v1/reclamos/seguimiento/{token}")
    assert habilitacion.json()["data"]["puede_iniciar"] is True
    reclamo = await client.post(
        f"/api/v1/reclamos/seguimiento/{token}",
        json={
            "tipo": "DEMORA",
            "numero_paquete": paquete,
            "descripcion": "El paquete figura en reparto desde temprano y todavía no llegó.",
            "contacto_nombre": "María Gómez",
            "contacto_telefono": "+54 9 3564 222222",
        },
    )
    assert reclamo.status_code == 201
    reclamo_id = reclamo.json()["data"]["id"]

    bandeja = await client.get("/api/v1/admin/reclamos", headers=admin, params={"estado": "ABIERTO"})
    assert [r["id"] for r in bandeja.json()["data"]] == [reclamo_id]
    cierre = await client.patch(
        f"/api/v1/admin/reclamos/{reclamo_id}/estado",
        headers=admin,
        json={"estado": "RESUELTO", "resolucion": "El repartidor confirmó la entrega para la tarde."},
    )
    assert cierre.status_code == 200

    vista_publica = await client.get(f"/api/v1/reclamos/seguimiento/{token}")
    assert vista_publica.json()["data"]["reclamos"][0]["estado"] == "RESUELTO"

    # --- HU08: las preguntas frecuentes explican cómo reclamar, sin iniciar sesión ---
    await sembrar_preguntas_frecuentes(db_session)
    faq = await client.get("/api/v1/preguntas-frecuentes", params={"categoria": "reclamos"})
    assert faq.status_code == 200
    assert faq.json()["data"]["total"] >= 1
