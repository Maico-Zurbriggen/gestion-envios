"""Monitor de envíos: tablero, listado filtrable, trazabilidad y exportación."""

import pytest
from httpx import AsyncClient

API = "/api/v1/admin/monitor"


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _envio(remitente: str, destinatario: str, paquetes: int = 1) -> dict:
    return {
        "remitente_nombre": remitente, "remitente_documento": "28111222", "remitente_telefono": "03564-15112233",
        "remitente_email": "remitente@empresa.com", "destinatario_nombre": destinatario,
        "destinatario_telefono": "+543564445566", "destinatario_email": "destinatario@gmail.com",
        "tipo_entrega": "sucursal", "sucursal_destino_id": 2, "sucursal_origen_id": 1, "terminos_aceptados": True,
        "paquetes": [
            {"descripcion": f"Caja {n + 1}", "peso_kg": 2, "largo_cm": 30, "ancho_cm": 20, "alto_cm": 10}
            for n in range(paquetes)
        ],
    }


async def _registrar(client: AsyncClient, remitente: str, destinatario: str, paquetes: int = 1) -> tuple[str, list[str]]:
    resp = await client.post("/api/v1/envios", json=_envio(remitente, destinatario, paquetes))
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    return data["token_seguimiento"], [p["numero_paquete"] for p in data["paquetes"]]


@pytest.mark.asyncio
async def test_permisos(client: AsyncClient, vendedor_token: str):
    assert (await client.get(f"{API}/resumen")).status_code == 401
    assert (await client.get(f"{API}/resumen", headers=_auth(vendedor_token))).status_code == 403
    assert (await client.get(f"{API}/paquetes", headers=_auth(vendedor_token))).status_code == 403


@pytest.mark.asyncio
async def test_resumen_y_listado_con_filtros(client: AsyncClient, administrativo_token: str):
    headers = _auth(administrativo_token)
    token_a, paquetes_a = await _registrar(client, "Carlos Gómez", "Lucía Morales", paquetes=2)
    _, paquetes_b = await _registrar(client, "Ana Ruiz", "Pedro Díaz")

    recepcion = await client.post(
        f"/api/v1/terminal/paquetes/{paquetes_b[0]}/recepcionar", headers=headers, json={"sucursal_id": 1}
    )
    assert recepcion.status_code == 200, recepcion.text

    resumen = (await client.get(f"{API}/resumen", headers=headers, params={"sucursal_id": 1})).json()["data"]
    assert resumen["total_paquetes"] == 3 and resumen["total_envios"] == 2
    assert resumen["por_grupo"]["PENDIENTES"] == 2 and resumen["por_grupo"]["EN_DEPOSITO"] == 1
    assert resumen["hoy"]["registrados"] == 3 and resumen["hoy"]["ingresados"] == 1
    assert resumen["sucursales"]

    todos = (await client.get(f"{API}/paquetes", headers=headers, params={"sucursal_id": 1})).json()["data"]
    assert todos["total"] == 3
    primero = todos["paquetes"][0]
    assert {"numero_paquete", "estado_etiqueta", "grupo", "destino", "recorrido"} <= primero.keys()

    pendientes = (await client.get(f"{API}/paquetes", headers=headers, params={"sucursal_id": 1, "grupo": "PENDIENTES"})).json()["data"]
    assert sorted(p["numero_paquete"] for p in pendientes["paquetes"]) == sorted(paquetes_a)

    en_deposito = (await client.get(f"{API}/paquetes", headers=headers, params={"sucursal_id": 1, "grupo": "EN_DEPOSITO"})).json()["data"]
    assert [p["numero_paquete"] for p in en_deposito["paquetes"]] == paquetes_b
    assert en_deposito["paquetes"][0]["sucursal_actual"]

    por_token = (await client.get(f"{API}/paquetes", headers=headers, params={"sucursal_id": 1, "buscar": token_a.lower()})).json()["data"]
    assert por_token["total"] == 2

    por_persona = (await client.get(f"{API}/paquetes", headers=headers, params={"sucursal_id": 1, "buscar": "pedro"})).json()["data"]
    assert [p["numero_paquete"] for p in por_persona["paquetes"]] == paquetes_b

    paginado = (await client.get(f"{API}/paquetes", headers=headers, params={"sucursal_id": 1, "por_pagina": 2, "pagina": 2})).json()["data"]
    assert paginado["paginas"] == 2 and len(paginado["paquetes"]) == 1

    invalido = await client.get(f"{API}/paquetes", headers=headers, params={"sucursal_id": 1, "grupo": "CUALQUIERA"})
    assert invalido.status_code == 400 and invalido.json()["errors"][0]["field"] == "grupo"


@pytest.mark.asyncio
async def test_trazabilidad_completa_con_reclamo(client: AsyncClient, administrativo_token: str):
    headers = _auth(administrativo_token)
    token, (paquete, hermano) = await _registrar(client, "Carlos Gómez", "Lucía Morales", paquetes=2)
    await client.post(
        f"/api/v1/terminal/paquetes/{paquete}/recepcionar",
        headers=headers,
        json={"sucursal_id": 1, "observaciones": "Caja en buen estado."},
    )
    reclamo = await client.post(
        f"/api/v1/reclamos/seguimiento/{token}",
        json={
            "tipo": "DEMORA", "numero_paquete": paquete, "contacto_nombre": "Lucía Morales",
            "descripcion": "El paquete figura en la terminal desde hace varios días.",
            "contacto_telefono": "+54 9 3564 222222",
        },
    )
    assert reclamo.status_code == 201

    resp = await client.get(f"{API}/paquetes/{paquete.lower()}", headers=headers)
    assert resp.status_code == 200, resp.text
    traza = resp.json()["data"]
    assert traza["paquete"]["numero_paquete"] == paquete
    assert traza["paquete"]["reclamos_en_curso"] == 1
    assert traza["remitente"]["documento"] == "28111222"
    assert {p["numero_paquete"] for p in traza["paquetes_del_envio"]} == {paquete, hermano}
    assert len(traza["reclamos"]) == 1 and traza["reclamos"][0]["tipo"] == "DEMORA"
    assert traza["notificaciones"], "los avisos del envío se informan en la traza"

    tipos = [e["tipo"] for e in traza["linea_de_tiempo"]]
    assert tipos[0] == "registro"
    assert "estado" in tipos and "reclamo" in tipos and "notificacion" in tipos
    recepcion = next(e for e in traza["linea_de_tiempo"] if e["tipo"] == "estado")
    assert recepcion["titulo"] == "En terminal de origen" and "Caja en buen estado." in recepcion["detalle"]
    fechas = [e["fecha"] for e in traza["linea_de_tiempo"]]
    assert fechas == sorted(fechas)

    con_reclamo = (await client.get(f"{API}/paquetes", headers=headers, params={"sucursal_id": 1, "grupo": "CON_RECLAMO"})).json()["data"]
    assert [p["numero_paquete"] for p in con_reclamo["paquetes"]] == [paquete]
    problemas = (await client.get(f"{API}/paquetes", headers=headers, params={"sucursal_id": 1, "grupo": "CON_PROBLEMAS"})).json()["data"]
    assert problemas["total"] == 1

    assert (await client.get(f"{API}/paquetes/PAQ-NOEXISTE", headers=headers)).status_code == 404


@pytest.mark.asyncio
async def test_firma_inexistente(client: AsyncClient, administrativo_token: str):
    resp = await client.get(
        f"{API}/entregas/7b0b4d55-5f0e-4b55-9b8a-0c1f6d9b2a11/firma", headers=_auth(administrativo_token)
    )
    assert resp.status_code == 404
