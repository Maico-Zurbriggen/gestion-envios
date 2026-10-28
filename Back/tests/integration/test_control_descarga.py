"""Control de descarga en la sucursal de destino: escanear lo que baja y compararlo con lo esperado."""

import pytest
from sqlalchemy import select

from app.infrastructure.db.models import AlertaRecorridoModel, HistorialEstadoPaqueteModel
from tests.integration.test_hu10_recorridos import _crear_paquete
from tests.integration.test_hu11_hu12_reparto import _armar

API = "/api/v1/terminal/descargas"


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_descarga_completa_con_sobrante_y_faltante(client, db_session, administrativo_token, vendedor_token):
    db_session.autoflush = False
    recorrido_id, paquetes, *_ = await _armar(client, db_session, administrativo_token, tipo="LARGA", cantidad=3)
    ajeno = (await _crear_paquete(db_session, cantidad=1, tipo_entrega="sucursal", sucursal_destino_id=2))[0]
    vendedor = _auth(vendedor_token)

    entrantes = await client.get(f"{API}/recorridos", headers=vendedor, params={"sucursal_id": 2})
    assert entrantes.status_code == 200, entrantes.text
    [entrante] = entrantes.json()["data"]
    assert entrante["recorrido_id"] == recorrido_id and entrante["esperados"] == 3 and entrante["control_id"] is None

    inicio = await client.post(API, headers=vendedor, json={"recorrido_id": recorrido_id, "sucursal_id": 2})
    assert inicio.status_code == 200, inicio.text
    control = inicio.json()["data"]
    assert control["total_esperados"] == 3 and control["verificados"] == 0 and control["estado"] == "EN_CURSO"
    retomado = await client.post(API, headers=vendedor, json={"recorrido_id": recorrido_id, "sucursal_id": 2})
    assert retomado.json()["data"]["id"] == control["id"], "iniciar dos veces retoma el mismo control"

    lectura = await client.post(f"{API}/{control['id']}/lecturas", headers=vendedor, json={"codigo": f" {paquetes[0].numero_paquete.lower()} "})
    assert lectura.status_code == 200, lectura.text
    dato = lectura.json()["data"]
    assert dato["resultado"] == "CORRECTO" and dato["control"]["verificados"] == 1
    await db_session.refresh(paquetes[0])
    assert paquetes[0].estado == "LISTO_PARA_RETIRO" and paquetes[0].sucursal_actual_id == 2
    assert paquetes[0].retiro_hasta is not None, "queda con fecha límite para retirarlo"
    assert dato["listo_para_retiro"] is True

    repetida = (await client.post(f"{API}/{control['id']}/lecturas", headers=vendedor, json={"codigo": paquetes[0].numero_paquete})).json()["data"]
    assert repetida["repetida"] is True and repetida["control"]["verificados"] == 1

    await client.post(f"{API}/{control['id']}/lecturas", headers=vendedor, json={"codigo": paquetes[1].numero_paquete})
    sobrante = (await client.post(f"{API}/{control['id']}/lecturas", headers=vendedor, json={"codigo": ajeno.numero_paquete})).json()["data"]
    assert sobrante["resultado"] == "SOBRANTE" and "No figura en este recorrido" in sobrante["mensaje"]
    desconocido = (await client.post(f"{API}/{control['id']}/lecturas", headers=vendedor, json={"codigo": "PAQ-ZZZZZZZZZZ"})).json()["data"]
    assert desconocido["resultado"] == "DESCONOCIDO"
    invalido = await client.post(f"{API}/{control['id']}/lecturas", headers=vendedor, json={"codigo": "ENV-123"})
    assert invalido.status_code == 400

    cierre = await client.post(f"{API}/{control['id']}/cerrar", headers=vendedor, json={"observaciones": "Faltó una caja."})
    assert cierre.status_code == 200, cierre.text
    cerrado = cierre.json()["data"]
    assert cerrado["estado"] == "CERRADO" and cerrado["verificados"] == 2 and cerrado["faltantes"] == 1
    assert len(cerrado["sobrantes"]) == 2
    assert "faltante" in cierre.json()["message"]

    alertas = (await db_session.scalars(select(AlertaRecorridoModel).where(AlertaRecorridoModel.motivo == "FALTANTE_EN_DESCARGA"))).all()
    assert [a.paquete_id for a in alertas] == [paquetes[2].id]
    recepciones = (await db_session.scalars(
        select(HistorialEstadoPaqueteModel).where(HistorialEstadoPaqueteModel.observacion.like("%control de descarga%"))
    )).all()
    assert len(recepciones) == 2

    despues = await client.post(f"{API}/{control['id']}/lecturas", headers=vendedor, json={"codigo": paquetes[2].numero_paquete})
    assert despues.status_code == 400, "un control cerrado no acepta lecturas"

    # El monitor muestra el faltante y la lectura en la trazabilidad.
    admin = _auth(administrativo_token)
    faltantes = (await client.get("/api/v1/admin/monitor/paquetes", headers=admin, params={"grupo": "FALTANTES"})).json()["data"]
    assert [p["numero_paquete"] for p in faltantes["paquetes"]] == [paquetes[2].numero_paquete]
    assert faltantes["paquetes"][0]["faltante_en_descarga"] is True
    sin_recorrido = (await client.get("/api/v1/admin/monitor/paquetes", headers=admin, params={"grupo": "SIN_RECORRIDO"})).json()["data"]
    assert paquetes[2].numero_paquete not in [p["numero_paquete"] for p in sin_recorrido["paquetes"]]
    traza = (await client.get(f"/api/v1/admin/monitor/paquetes/{paquetes[0].numero_paquete}", headers=admin)).json()["data"]
    assert any(e["tipo"] == "descarga" and e["titulo"] == "Verificado en la descarga" for e in traza["linea_de_tiempo"])
    resumen = (await client.get("/api/v1/admin/monitor/resumen", headers=admin)).json()["data"]
    assert resumen["faltantes"] == 1


@pytest.mark.asyncio
async def test_validaciones_al_iniciar(client, db_session, administrativo_token, vendedor_token):
    vendedor = _auth(vendedor_token)
    corta_id, *_ = await _armar(client, db_session, administrativo_token, tipo="CORTA", cantidad=1)
    corta = await client.post(API, headers=vendedor, json={"recorrido_id": corta_id, "sucursal_id": 2})
    assert corta.status_code == 400

    larga_id, *_ = await _armar(client, db_session, administrativo_token, tipo="LARGA", cantidad=1, iniciar=False)
    sin_salir = await client.post(API, headers=vendedor, json={"recorrido_id": larga_id, "sucursal_id": 2})
    assert sin_salir.status_code == 400 and "todavía no salió" in sin_salir.json()["message"]

    assert (await client.get(f"{API}/recorridos", params={"sucursal_id": 2})).status_code == 401


@pytest.mark.asyncio
async def test_control_de_carga_quita_lo_que_no_subio(client, db_session, administrativo_token, vendedor_token):
    db_session.autoflush = False
    recorrido_id, paquetes, *_ = await _armar(client, db_session, administrativo_token, tipo="LARGA", cantidad=3, iniciar=False)
    vendedor = _auth(vendedor_token)

    salientes = (await client.get(f"{API}/recorridos-salientes", headers=vendedor, params={"sucursal_id": 1})).json()["data"]
    assert [r["recorrido_id"] for r in salientes] == [recorrido_id] and salientes[0]["esperados"] == 3

    otra = await client.post(API, headers=vendedor, json={"recorrido_id": recorrido_id, "sucursal_id": 2, "tipo": "CARGA"})
    assert otra.status_code == 400, "la carga se controla en la sucursal de origen"
    control = (await client.post(API, headers=vendedor, json={"recorrido_id": recorrido_id, "sucursal_id": 1, "tipo": "CARGA"})).json()["data"]
    assert control["tipo"] == "CARGA" and control["total_esperados"] == 3

    for paquete in paquetes[:2]:
        lectura = (await client.post(f"{API}/{control['id']}/lecturas", headers=vendedor, json={"codigo": paquete.numero_paquete})).json()["data"]
        assert lectura["resultado"] == "CORRECTO" and lectura["listo_para_retiro"] is False

    cierre = await client.post(f"{API}/{control['id']}/cerrar", headers=vendedor, json={})
    assert cierre.status_code == 200, cierre.text
    assert "salieron del recorrido" in cierre.json()["message"]

    detalle = (await client.get(f"/api/v1/recorridos/{recorrido_id}", headers=_auth(administrativo_token))).json()["data"]
    en_recorrido = {p["numero_paquete"] for parada in detalle["paradas"] for p in parada["paquetes"]}
    assert en_recorrido == {paquetes[0].numero_paquete, paquetes[1].numero_paquete}
    alertas = (await db_session.scalars(select(AlertaRecorridoModel).where(AlertaRecorridoModel.motivo == "FALTANTE_EN_CARGA"))).all()
    assert [a.paquete_id for a in alertas] == [paquetes[2].id]
