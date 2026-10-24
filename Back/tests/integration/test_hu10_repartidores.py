"""Tests de integración de los perfiles de repartidor (soporte de HU10).

Sin sucursal base ni tipo de reparto, un usuario REPARTIDOR no puede recibir
recorridos (HU10 Escenarios 1 y 4).
"""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.constants.error_codes import ErrorCodes
from app.domain.constants.estados_logistica import EstadoRecorridoEnum
from app.infrastructure.db.models import RecorridoModel, RepartidorModel

BASE = "/api/v1/repartidores"


@pytest.mark.asyncio
async def test_hu10_repartidores_requiere_rol_de_logistica(
    client: AsyncClient, vendedor_token: str, repartidor_token: str, administrativo_token: str, superadmin_token: str
):
    assert (await client.get(BASE)).status_code == 401
    for token in (vendedor_token, repartidor_token):
        resp = await client.get(BASE, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
        assert resp.json()["code"] == ErrorCodes.FORBIDDEN_ACCESS
    assert (await client.get(BASE, headers={"Authorization": f"Bearer {administrativo_token}"})).status_code == 200


@pytest.mark.asyncio
async def test_hu10_lista_repartidores_sin_perfil(
    client: AsyncClient, administrativo_token: str, repartidor_usuario
):
    resp = await client.get(BASE, headers={"Authorization": f"Bearer {administrativo_token}"})

    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    data = resp.json()["data"][0]
    assert data["usuario_id"] == str(repartidor_usuario.id)
    assert data["perfil_configurado"] is False
    assert data["disponible_para_recorridos"] is False
    assert data["sucursal_base"] is None


@pytest.mark.asyncio
async def test_hu10_configurar_perfil_de_repartidor(
    client: AsyncClient, administrativo_token: str, repartidor_usuario
):
    headers = {"Authorization": f"Bearer {administrativo_token}"}

    alta = await client.put(
        f"{BASE}/{repartidor_usuario.id}/perfil",
        headers=headers,
        json={"sucursal_base_id": 1, "tipo_reparto": "corta"},
    )
    assert alta.status_code == 200
    assert alta.json()["message"] == "Perfil de repartidor creado."
    data = alta.json()["data"]
    assert data["perfil_configurado"] is True
    assert data["tipo_reparto"] == "CORTA"
    assert data["activo"] is True
    assert data["sucursal_base"]["id"] == 1
    assert data["disponible_para_recorridos"] is True

    cambio = await client.put(
        f"{BASE}/{repartidor_usuario.id}/perfil",
        headers=headers,
        json={"sucursal_base_id": 2, "tipo_reparto": "LARGA", "activo": False},
    )
    assert cambio.status_code == 200
    assert cambio.json()["message"] == "Perfil de repartidor actualizado."
    assert cambio.json()["data"]["sucursal_base"]["id"] == 2
    assert cambio.json()["data"]["disponible_para_recorridos"] is False

    filtrado = await client.get(BASE, headers=headers, params={"sucursal_id": 2, "tipo_reparto": "larga"})
    assert filtrado.json()["total"] == 1
    assert (await client.get(BASE, headers=headers, params={"sucursal_id": 1})).json()["total"] == 0
    assert (await client.get(BASE, headers=headers, params={"activo": True})).json()["total"] == 0


@pytest.mark.asyncio
async def test_hu10_perfil_validaciones(
    client: AsyncClient, administrativo_token: str, repartidor_usuario, vendedor_usuario
):
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    url = f"{BASE}/{repartidor_usuario.id}/perfil"

    tipo_invalido = await client.put(url, headers=headers, json={"sucursal_base_id": 1, "tipo_reparto": "MEDIA"})
    assert tipo_invalido.status_code == 400

    sucursal_inexistente = await client.put(url, headers=headers, json={"sucursal_base_id": 999, "tipo_reparto": "CORTA"})
    assert sucursal_inexistente.status_code == 400
    assert sucursal_inexistente.json()["errors"][0]["field"] == "sucursal_base_id"

    no_repartidor = await client.put(
        f"{BASE}/{vendedor_usuario.id}/perfil", headers=headers, json={"sucursal_base_id": 1, "tipo_reparto": "CORTA"}
    )
    assert no_repartidor.status_code == 400
    assert no_repartidor.json()["errors"][0]["field"] == "usuario_id"

    inexistente = await client.put(
        f"{BASE}/{uuid.uuid4()}/perfil", headers=headers, json={"sucursal_base_id": 1, "tipo_reparto": "CORTA"}
    )
    assert inexistente.status_code == 404

    filtro_invalido = await client.get(BASE, headers=headers, params={"tipo_reparto": "MEDIA"})
    assert filtro_invalido.status_code == 400


@pytest.mark.asyncio
async def test_hu10_no_cambia_operacion_con_recorridos_activos(
    client: AsyncClient, db_session: AsyncSession, administrativo_token: str, repartidor_usuario
):
    headers = {"Authorization": f"Bearer {administrativo_token}"}
    db_session.add(RepartidorModel(usuario_id=repartidor_usuario.id, sucursal_base_id=1, tipo_reparto="CORTA"))
    await db_session.commit()
    db_session.add(
        RecorridoModel(
            repartidor_id=repartidor_usuario.id,
            sucursal_origen_id=1,
            tipo_distancia="CORTA",
            fecha=date.today(),
            estado=EstadoRecorridoEnum.GENERADO.value,
        )
    )
    await db_session.commit()
    url = f"{BASE}/{repartidor_usuario.id}/perfil"

    resp = await client.put(url, headers=headers, json={"sucursal_base_id": 2, "tipo_reparto": "CORTA"})
    assert resp.status_code == 409

    desactivar = await client.put(url, headers=headers, json={"sucursal_base_id": 1, "tipo_reparto": "CORTA", "activo": False})
    assert desactivar.status_code == 409

    # Reenviar el mismo perfil no cambia la operación: se permite
    igual = await client.put(url, headers=headers, json={"sucursal_base_id": 1, "tipo_reparto": "CORTA"})
    assert igual.status_code == 200


@pytest.mark.asyncio
async def test_hu10_detalle_de_repartidor(client: AsyncClient, administrativo_token: str, repartidor_usuario):
    headers = {"Authorization": f"Bearer {administrativo_token}"}

    resp = await client.get(f"{BASE}/{repartidor_usuario.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["nombre"] == repartidor_usuario.nombre

    assert (await client.get(f"{BASE}/{uuid.uuid4()}", headers=headers)).status_code == 404
