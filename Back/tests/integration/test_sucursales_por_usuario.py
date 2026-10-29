"""Todo se divide por sucursal: cada usuario entra solo en las que tiene habilitadas."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.constants.roles import RolIdEnum
from app.infrastructure.db.models import SucursalModel


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _login(client: AsyncClient, dni: str, password: str) -> dict:
    resp = await client.post("/api/v1/auth/login", json={"dni": dni, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _superadmin(client: AsyncClient) -> str:
    datos = await _login(client, settings.SUPERADMIN_SEED_DNI, settings.SUPERADMIN_SEED_PASSWORD or "SuperAdmin2026!*")
    return datos["token"]


def _sucursal(nombre: str = "Sucursal Villa María", **extra) -> dict:
    return {
        "nombre": nombre, "provincia": "Córdoba", "ciudad": "Villa María", "direccion": "San Martín 100",
        "latitud": -32.41, "longitud": -63.24, **extra,
    }


@pytest.mark.asyncio
async def test_el_login_informa_las_sucursales_habilitadas(client: AsyncClient, db_session: AsyncSession):
    token = await _superadmin(client)
    db_session.add(SucursalModel(nombre="Sucursal Cerrada", provincia="Salta", ciudad="Salta", direccion="X 1", activa=False))
    await db_session.commit()
    creado = await client.post("/api/v1/admin/empleados", headers=_auth(token), json={
        "nombre": "Vera Vendedora", "dni": "40111222", "email": "vera@demo.example.com", "telefono": "+543564111222",
        "rol_id": RolIdEnum.VENDEDOR.value, "sucursal_ids": [2],
    })
    assert creado.status_code == 201, creado.text
    assert [s["id"] for s in creado.json()["data"]["sucursales"]] == [2]

    # Con la clave temporal primero tiene que cambiarla; el detalle del usuario ya muestra su sucursal.
    detalle = (await client.get(f"/api/v1/admin/empleados/{creado.json()['data']['id']}", headers=_auth(token))).json()
    assert [s["id"] for s in detalle["data"]["sucursales"]] == [2]

    # El Superadministrador entra en todas, también en las inactivas.
    me = (await client.get("/api/v1/auth/me", headers=_auth(token))).json()["data"]["user"]
    assert {s["nombre"] for s in me["sucursales"]} >= {"Sucursal Test Centro", "Sucursal Test Norte", "Sucursal Cerrada"}


@pytest.mark.asyncio
async def test_sin_sucursal_habilitada_no_se_opera(
    client: AsyncClient, db_session: AsyncSession, administrativo_usuario, administrativo_token: str
):
    administrativo_usuario.sucursales = [await db_session.get(SucursalModel, 1)]
    await db_session.commit()
    headers = _auth(administrativo_token)

    propia = await client.get("/api/v1/recorridos/pendientes", headers=headers, params={"sucursal_id": 1, "tipo_distancia": "CORTA"})
    assert propia.status_code == 200
    ajena = await client.get("/api/v1/recorridos/pendientes", headers=headers, params={"sucursal_id": 2, "tipo_distancia": "CORTA"})
    assert ajena.status_code == 403
    assert (await client.get("/api/v1/admin/monitor/resumen", headers=headers, params={"sucursal_id": 2})).status_code == 403
    # Sin decir la sucursal, el listado la pide.
    assert (await client.get("/api/v1/admin/monitor/resumen", headers=headers)).status_code == 400


@pytest.mark.asyncio
async def test_abm_de_sucursales_con_su_punto_de_partida(client: AsyncClient, administrativo_token: str):
    token = await _superadmin(client)
    assert (await client.get("/api/v1/admin/sucursales", headers=_auth(administrativo_token))).status_code == 403

    sin_ubicacion = _sucursal()
    del sin_ubicacion["latitud"]
    assert (await client.post("/api/v1/admin/sucursales", headers=_auth(token), json=sin_ubicacion)).status_code in (400, 422)

    creada = await client.post("/api/v1/admin/sucursales", headers=_auth(token), json=_sucursal())
    assert creada.status_code == 201, creada.text
    sucursal = creada.json()["data"]
    assert sucursal["activa"] is True and sucursal["latitud"] == -32.41

    repetida = await client.post("/api/v1/admin/sucursales", headers=_auth(token), json=_sucursal("sucursal villa maría"))
    assert repetida.status_code == 409

    publicas = (await client.get("/api/v1/sucursales")).json()["data"]
    assert sucursal["id"] in {s["id"] for s in publicas}

    # Inactiva: deja de ofrecerse para envíos nuevos, pero se sigue administrando.
    editada = await client.put(
        f"/api/v1/admin/sucursales/{sucursal['id']}", headers=_auth(token),
        json=_sucursal(direccion="Belgrano 250", activa=False),
    )
    assert editada.status_code == 200, editada.text
    assert editada.json()["data"]["direccion"] == "Belgrano 250"
    assert sucursal["id"] not in {s["id"] for s in (await client.get("/api/v1/sucursales")).json()["data"]}
    todas = (await client.get("/api/v1/admin/sucursales", headers=_auth(token))).json()["data"]
    assert any(s["id"] == sucursal["id"] and s["activa"] is False for s in todas)
    assert (await client.put("/api/v1/admin/sucursales/999", headers=_auth(token), json=_sucursal("Otra"))).status_code == 404


@pytest.mark.asyncio
async def test_vendedor_y_administrativo_necesitan_una_sucursal(client: AsyncClient):
    token = await _superadmin(client)
    base = {"nombre": "Sin Sucursal", "dni": "40999888", "email": "sin@demo.example.com", "telefono": "+543564999888"}
    sin = await client.post("/api/v1/admin/empleados", headers=_auth(token), json={**base, "rol_id": RolIdEnum.ADMINISTRATIVO.value})
    assert sin.status_code == 400
    assert sin.json()["errors"][0]["field"] == "sucursal_ids"
    inexistente = await client.post(
        "/api/v1/admin/empleados", headers=_auth(token), json={**base, "rol_id": RolIdEnum.VENDEDOR.value, "sucursal_ids": [99]}
    )
    assert inexistente.status_code == 400

    creado = await client.post(
        "/api/v1/admin/empleados", headers=_auth(token), json={**base, "rol_id": RolIdEnum.VENDEDOR.value, "sucursal_ids": [1]}
    )
    assert creado.status_code == 201, creado.text
    id_ = creado.json()["data"]["id"]
    cambio = await client.patch(f"/api/v1/admin/empleados/{id_}", headers=_auth(token), json={"sucursal_ids": [1, 2]})
    assert cambio.status_code == 200, cambio.text
    assert [s["id"] for s in cambio.json()["data"]["sucursales"]] == [1, 2]
    vacio = await client.patch(f"/api/v1/admin/empleados/{id_}", headers=_auth(token), json={"sucursal_ids": []})
    assert vacio.status_code == 400


@pytest.mark.asyncio
async def test_el_envio_exige_la_sucursal_de_origen(client: AsyncClient, db_session: AsyncSession, administrativo_token: str):
    envio = {
        "remitente_nombre": "Ana Ruiz", "remitente_documento": "28111222", "remitente_telefono": "03564-15112233",
        "remitente_email": "ana@demo.example.com", "destinatario_nombre": "Pedro Díaz",
        "destinatario_telefono": "+543564445566", "destinatario_email": "pedro@demo.example.com",
        "tipo_entrega": "sucursal", "sucursal_destino_id": 1, "terminos_aceptados": True,
        "paquetes": [{"descripcion": "Caja", "peso_kg": 2, "largo_cm": 30, "ancho_cm": 20, "alto_cm": 10}],
    }
    assert (await client.post("/api/v1/envios", json=envio)).status_code in (400, 422)

    db_session.add(SucursalModel(id=7, nombre="Cerrada", provincia="Salta", ciudad="Salta", direccion="X 1", activa=False))
    await db_session.commit()
    inactiva = await client.post("/api/v1/envios", json={**envio, "sucursal_origen_id": 7})
    assert inactiva.status_code == 400
    assert inactiva.json()["errors"][0]["field"] == "sucursal_origen_id"

    creado = await client.post("/api/v1/envios", json={**envio, "sucursal_origen_id": 2})
    assert creado.status_code == 201, creado.text
    assert creado.json()["data"]["sucursal_origen"]["id"] == 2

    # El registrado sin llegar cuenta para la sucursal donde lo van a llevar.
    resumen = (await client.get("/api/v1/recorridos/pendientes/resumen", headers=_auth(administrativo_token))).json()["data"]
    assert resumen["sin_llegar"] == 1
    assert [(s["sucursal_id"], s["sin_llegar"]) for s in resumen["sucursales"]] == [(2, 1)]


@pytest.mark.asyncio
async def test_el_repartidor_pertenece_a_una_sola_sucursal_y_es_su_base(client: AsyncClient, administrativo_token: str):
    token = await _superadmin(client)
    base = {"nombre": "Rita Repartidora", "dni": "40777666", "email": "rita@demo.example.com", "telefono": "+543564777666",
            "rol_id": RolIdEnum.REPARTIDOR.value}
    assert (await client.post("/api/v1/admin/empleados", headers=_auth(token), json=base)).status_code == 400
    dos = await client.post("/api/v1/admin/empleados", headers=_auth(token), json={**base, "sucursal_ids": [1, 2]})
    assert dos.status_code == 400 and dos.json()["errors"][0]["field"] == "sucursal_ids"

    creado = await client.post("/api/v1/admin/empleados", headers=_auth(token), json={**base, "sucursal_ids": [1]})
    assert creado.status_code == 201, creado.text
    id_ = creado.json()["data"]["id"]

    # Configurar la base de reparto en la otra sucursal cambia también la sucursal del usuario.
    perfil = await client.put(f"/api/v1/repartidores/{id_}/perfil", headers=_auth(administrativo_token),
                              json={"sucursal_base_id": 2, "tipo_reparto": "CORTA", "activo": True})
    assert perfil.status_code == 200, perfil.text
    detalle = (await client.get(f"/api/v1/admin/empleados/{id_}", headers=_auth(token))).json()["data"]
    assert [s["id"] for s in detalle["sucursales"]] == [2]

    # Y al revés: cambiarlo de sucursal en Usuarios mueve su base de reparto.
    cambio = await client.patch(f"/api/v1/admin/empleados/{id_}", headers=_auth(token), json={"sucursal_ids": [1]})
    assert cambio.status_code == 200, cambio.text
    repartidor = (await client.get(f"/api/v1/repartidores/{id_}", headers=_auth(administrativo_token))).json()["data"]
    assert repartidor["sucursal_base"]["id"] == 1


@pytest.mark.asyncio
async def test_al_cambiar_de_rol_se_revalidan_las_sucursales(client: AsyncClient):
    token = await _superadmin(client)
    creado = await client.post("/api/v1/admin/empleados", headers=_auth(token), json={
        "nombre": "Vale Vendedora", "dni": "40555444", "email": "vale@demo.example.com", "telefono": "+543564555444",
        "rol_id": RolIdEnum.VENDEDOR.value, "sucursal_ids": [1, 2],
    })
    id_ = creado.json()["data"]["id"]
    # Con dos sucursales no puede pasar a repartidor sin elegir una.
    a_repartidor = await client.patch(f"/api/v1/admin/empleados/{id_}", headers=_auth(token), json={"rol_id": RolIdEnum.REPARTIDOR.value})
    assert a_repartidor.status_code == 400
    ok = await client.patch(f"/api/v1/admin/empleados/{id_}", headers=_auth(token),
                            json={"rol_id": RolIdEnum.REPARTIDOR.value, "sucursal_ids": [2]})
    assert ok.status_code == 200, ok.text
    assert [s["id"] for s in ok.json()["data"]["sucursales"]] == [2]
