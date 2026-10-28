import base64
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from app.api.dependencies import obtener_sesion_db
from app.api.main import app
from app.application.services.servicio_notificaciones import ServicioNotificaciones
from app.domain.constants.roles import RolEnum
from app.domain.constants.scopes import ScopeEnum
from app.infrastructure.auth.jwt_handler import ManejadorJWT
from app.infrastructure.db.models import (
    EnvioModel,
    EventoEntregaModel,
    HistorialEstadoPaqueteModel,
    NotificacionEnvioModel,
    PaqueteModel,
    PosicionActualRepartidorModel,
    RecorridoPaqueteModel,
    RepartidorModel,
    SucursalModel,
)
from app.infrastructure.email import email_provider
from app.infrastructure.email.email_provider import MockEmailProvider
from app.infrastructure.repositories.repositorio_recorridos import RepositorioRecorridos
from tests.conftest import TestingSessionLocal
from tests.integration.test_hu10_recorridos import _crear_paquete, _crear_repartidor, _generar
from tests.unit.test_reparto_rules import crear_png

BASE = "/api/v1/reparto/recorridos"


def _headers(usuario, scope=ScopeEnum.FULL_ACCESS.value):
    token = ManejadorJWT.emitir_token(usuario_id=str(usuario.id), rol=RolEnum.REPARTIDOR.value, scope=scope)
    return {"Authorization": f"Bearer {token}"}


def _olvidar_aviso_de_reparto(variables):
    """Al iniciar un recorrido corto sale el aviso «hoy entregamos tu paquete»; estas pruebas miran la visita."""
    for nombre in ("correo", "whatsapp"):
        proveedor = variables.get(nombre)
        if proveedor is not None and hasattr(proveedor, "mensajes_enviados"):
            proveedor.mensajes_enviados.clear()


def _constancia(**cambios):
    return {
        "operacion_id": str(uuid.uuid4()),
        "receptor_nombre": "Persona Receptora",
        "receptor_documento": "30111222",
        "receptor_fecha_nacimiento": "2000-01-01",
        "es_autorizado": True,
        "firma_base64": base64.b64encode(crear_png()).decode(),
        **cambios,
    }


async def _armar(client, db, admin_token, *, tipo="CORTA", iniciar=True, cantidad=2, usuario=None):
    usuario = usuario or await _crear_repartidor(db, "Repartidor HU11", tipo=tipo)
    opciones = (
        {"latitud": -31.41, "longitud": -64.19}
        if tipo == "CORTA"
        else {"tipo_entrega": "sucursal", "sucursal_destino_id": 2}
    )
    paquetes = await _crear_paquete(db, cantidad=cantidad, **opciones)
    recorrido = (await _generar(client, admin_token, tipo_distancia=tipo))["data"]["recorridos"][0]
    id_ = recorrido["id"]
    headers = _headers(usuario)
    if iniciar:
        respuesta = await client.post(f"{BASE}/{id_}/iniciar", headers=headers)
        assert respuesta.status_code == 200, respuesta.text
    envio = await db.get(EnvioModel, paquetes[0].envio_id)
    return id_, paquetes, usuario, headers, envio.token_seguimiento


@pytest.fixture
def correo(monkeypatch):
    proveedor = MockEmailProvider()
    monkeypatch.setattr(email_provider, "_email_provider_instance", proveedor)
    return proveedor


async def test_hu11_escenario_1_mis_recorridos_y_mapa(client, db_session, administrativo_token):
    id_, paquetes, usuario, headers, _ = await _armar(client, db_session, administrativo_token, iniciar=False)
    listado = await client.get(BASE, headers=headers)
    assert listado.status_code == 200
    assert [r["id"] for r in listado.json()["data"]] == [id_]
    detalle = await client.get(f"{BASE}/{id_}", headers=headers)
    assert detalle.status_code == 200
    mapa = detalle.json()["data"]
    assert mapa["sucursal_origen"]["id"] == 1
    assert mapa["paradas"][0]["latitud"] == -31.41
    assert [p["orden"] for p in mapa["paradas"][0]["paquetes"]] == [1, 2]
    assert len(mapa["trazado"]) == 3
    assert (await client.get(f"{BASE}?estado=EN_CURSO", headers=headers)).json()["total"] == 0
    assert (await client.get(f"{BASE}?estado=INVALIDO", headers=headers)).status_code == 400


async def test_hu11_aislamiento_de_recorridos_y_roles(
    client,
    db_session,
    administrativo_token,
    vendedor_token,
    repartidor_token,
):
    id_, paquetes, _, headers, _ = await _armar(client, db_session, administrativo_token)
    _olvidar_aviso_de_reparto(locals())
    otro = await _crear_repartidor(db_session, "Otro repartidor")
    ajeno = _headers(otro)
    assert (await client.get(BASE, headers=ajeno)).json()["data"] == []
    for ruta in (f"/{id_}", f"/{id_}/ubicacion", f"/{id_}/paquetes/{paquetes[0].id}/contacto"):
        assert (await client.get(BASE + ruta, headers=ajeno)).status_code == 404
    assert (
        await client.put(f"{BASE}/{id_}/ubicacion", headers=ajeno, json={"latitud": 0, "longitud": 0})
    ).status_code == 404
    for ruta, datos in (
        ("entrega", _constancia()),
        (
            "visita-fallida",
            {
                "operacion_id": str(uuid.uuid4()),
                "motivo_fallo": "Ausente",
            },
        ),
    ):
        assert (
            await client.post(f"{BASE}/{id_}/paquetes/{paquetes[0].id}/{ruta}", headers=ajeno, json=datos)
        ).status_code == 404
    for h, esperado in (
        ({}, 401),
        ({"Authorization": f"Bearer {vendedor_token}"}, 403),
        ({"Authorization": f"Bearer {administrativo_token}"}, 403),
        ({"Authorization": f"Bearer {repartidor_token}"}, 403),
        (_headers(otro, ScopeEnum.PASSWORD_RESET_ONLY.value), 403),
    ):
        assert (await client.get(BASE, headers=h)).status_code == esperado
    assert (await client.get(f"{BASE}/{uuid.uuid4()}", headers=headers)).status_code == 404


async def test_hu11_escenario_2_ubicacion_corta_no_modifica_estados(client, db_session, administrativo_token):
    id_, paquetes, usuario, headers, token = await _armar(client, db_session, administrativo_token)
    _olvidar_aviso_de_reparto(locals())
    assert (await client.get(f"{BASE}/{id_}/ubicacion", headers=headers)).json()["data"] is None
    for lat in (-31.42, -31.43):
        resp = await client.put(f"{BASE}/{id_}/ubicacion", headers=headers, json={"latitud": lat, "longitud": -64.2})
        assert resp.status_code == 200, resp.text
        assert resp.json()["paquetes_actualizados"] == []
    posicion = await db_session.get(PosicionActualRepartidorModel, usuario.id, populate_existing=True)
    assert posicion.latitud == -31.43
    assert str(posicion.recorrido_id) == id_
    assert (await db_session.scalar(select(func.count()).select_from(PosicionActualRepartidorModel))) == 1
    for paquete in paquetes:
        await db_session.refresh(paquete)
        assert paquete.estado == "EN_REPARTO"
    seguimiento = (await client.get(f"/api/v1/seguimiento/{token}")).json()["data"]
    assert all(p["ubicacion_repartidor"]["latitud"] == -31.43 for p in seguimiento["paquetes"])
    assert all(len(p["historial"]) == 1 for p in seguimiento["paquetes"])
    assert "repartidor_id" not in str(seguimiento)
    assert "destinatario_telefono" not in str(seguimiento)


@pytest.mark.parametrize(
    "datos",
    [
        {"latitud": 91, "longitud": 0},
        {"latitud": 0, "longitud": -181},
        {"latitud": "NaN", "longitud": 0},
        {"latitud": 0, "longitud": "Infinity"},
        {"latitud": 0},
        {"latitud": 0, "longitud": 0, "repartidor_id": str(uuid.uuid4())},
    ],
)
async def test_hu11_rechaza_coordenadas_invalidas(client, db_session, administrativo_token, datos):
    id_, _, usuario, headers, _ = await _armar(client, db_session, administrativo_token)
    _olvidar_aviso_de_reparto(locals())
    resp = await client.put(f"{BASE}/{id_}/ubicacion", headers=headers, json=datos)
    assert resp.status_code == 400, resp.text
    assert await db_session.get(PosicionActualRepartidorModel, usuario.id) is None


async def test_hu11_rechaza_operaciones_sin_recorrido_activo(client, db_session, administrativo_token):
    id_, paquetes, _, headers, _ = await _armar(client, db_session, administrativo_token, iniciar=False)
    assert (
        await client.put(f"{BASE}/{id_}/ubicacion", headers=headers, json={"latitud": -31.4, "longitud": -64.18})
    ).status_code == 400
    assert (
        await client.post(f"{BASE}/{id_}/paquetes/{paquetes[0].id}/entrega", headers=headers, json=_constancia())
    ).status_code == 400
    assert (
        await client.post(
            f"{BASE}/{id_}/paquetes/{paquetes[0].id}/visita-fallida",
            headers=headers,
            json={"operacion_id": str(uuid.uuid4()), "motivo_fallo": "Ausente"},
        )
    ).status_code == 400


async def test_hu11_escenario_3_proximidad_larga_y_sin_duplicados(client, db_session, administrativo_token):
    db_session.autoflush = False  # misma configuración que la sesión de producción
    id_, paquetes, _, headers, token = await _armar(client, db_session, administrativo_token, tipo="LARGA")
    # Fuera del radio: no hay cambios.
    lejos = await client.put(f"{BASE}/{id_}/ubicacion", headers=headers, json={"latitud": -32.7, "longitud": -60.69})
    assert lejos.status_code == 200
    assert lejos.json()["paquetes_actualizados"] == []
    cerca = await client.put(f"{BASE}/{id_}/ubicacion", headers=headers, json={"latitud": -32.94, "longitud": -60.69})
    assert cerca.status_code == 200, cerca.text
    assert set(cerca.json()["paquetes_actualizados"]) == {str(p.id) for p in paquetes}
    for paquete in paquetes:
        await db_session.refresh(paquete)
        assert paquete.estado == "EN_SUCURSAL_DESTINO"
        assert paquete.sucursal_actual_id == 2
    repetida = await client.put(
        f"{BASE}/{id_}/ubicacion", headers=headers, json={"latitud": -32.94, "longitud": -60.69}
    )
    assert repetida.status_code == 400  # recorrido finalizado
    historial = list(
        (
            await db_session.scalars(
                select(HistorialEstadoPaqueteModel).where(
                    HistorialEstadoPaqueteModel.estado_nuevo == "EN_SUCURSAL_DESTINO",
                )
            )
        ).all()
    )
    assert len(historial) == 2
    assert all(h.usuario_id is None and h.sucursal_id == 2 for h in historial)
    publico = (await client.get(f"/api/v1/seguimiento/{token}")).json()["data"]["paquetes"]
    assert all(p["estado"] == "EN_SUCURSAL_DESTINO" and p["ubicacion_repartidor"] is None for p in publico)


async def test_hu11_respeta_siguiente_sucursal_y_no_anticipa_otro_tramo(client, db_session, administrativo_token):
    # Dos sucursales a menos de 10 km entre sí: sólo la primera parada debe cambiar por ping.
    db_session.add(
        SucursalModel(
            id=3,
            nombre="Rosario Este",
            ciudad="Rosario",
            provincia="Santa Fe",
            direccion="Otra 123",
            latitud=-32.96,
            longitud=-60.69,
        )
    )
    await db_session.commit()
    usuario = await _crear_repartidor(db_session, "Larga distancia", tipo="LARGA")
    p2 = (await _crear_paquete(db_session, tipo_entrega="sucursal", sucursal_destino_id=2))[0]
    p3 = (await _crear_paquete(db_session, tipo_entrega="sucursal", sucursal_destino_id=3))[0]
    r = (await _generar(client, administrativo_token, tipo_distancia="LARGA"))["data"]["recorridos"][0]
    headers = _headers(usuario)
    assert (await client.post(f"{BASE}/{r['id']}/iniciar", headers=headers)).status_code == 200
    primera = r["paradas"][0]
    resp = await client.put(
        f"{BASE}/{r['id']}/ubicacion",
        headers=headers,
        json={"latitud": primera["latitud"], "longitud": primera["longitud"]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["paquetes_actualizados"] == [primera["paquetes"][0]["paquete_id"]]
    for p in (p2, p3):
        await db_session.refresh(p)
    assert {p2.estado, p3.estado} == {"EN_TRANSITO", "EN_SUCURSAL_DESTINO"}


async def test_hu12_escenario_1_entrega_firma_receptor_e_historial(client, db_session, administrativo_token):
    id_, paquetes, usuario, headers, token = await _armar(client, db_session, administrativo_token)
    _olvidar_aviso_de_reparto(locals())
    cuerpo = _constancia()
    url = f"{BASE}/{id_}/paquetes/{paquetes[0].numero_paquete}/entrega"
    antes = datetime.now(UTC)
    respuesta = await client.post(url, headers=headers, json=cuerpo)
    assert respuesta.status_code == 200, respuesta.text
    data = respuesta.json()["data"]
    evento = await db_session.get(EventoEntregaModel, uuid.UUID(data["evento_id"]))
    assert evento.firma_imagen == crear_png()
    assert evento.receptor_nombre == cuerpo["receptor_nombre"]
    assert evento.receptor_documento == cuerpo["receptor_documento"]
    assert evento.receptor_fecha_nacimiento.isoformat() == "2000-01-01"
    assert evento.usuario_registro_id == usuario.id
    assert evento.created_at.replace(tzinfo=UTC) >= antes
    await db_session.refresh(paquetes[0])
    assert paquetes[0].estado == "ENTREGADO"
    firma = await client.get(f"{BASE}/{id_}/entregas/{evento.id}/firma", headers=headers)
    assert firma.status_code == 200
    assert firma.content == crear_png()
    assert firma.headers["cache-control"] == "no-store"
    assert firma.headers["content-type"] == "image/png"
    assert (await client.get(f"{BASE}/{id_}/entregas/{evento.id}/firma")).status_code == 401
    otra_persona = await _crear_repartidor(db_session, "Otro")
    assert (
        await client.get(f"{BASE}/{id_}/entregas/{evento.id}/firma", headers=_headers(otra_persona))
    ).status_code == 404
    repetida = await client.post(url, headers=headers, json=cuerpo)
    assert repetida.status_code == 200
    assert repetida.json() == respuesta.json()
    assert (await client.post(url, headers=headers, json=_constancia())).status_code == 409
    assert (await client.post(url, headers=headers, json={**cuerpo, "receptor_nombre": "Cambio"})).status_code == 409
    assert await db_session.scalar(select(func.count()).select_from(EventoEntregaModel)) == 1
    publico = (await client.get(f"/api/v1/seguimiento/{token}")).json()["data"]
    p = next(p for p in publico["paquetes"] if p["numero_paquete"] == paquetes[0].numero_paquete)
    assert p["historial"][-1]["estado"] == "ENTREGADO"
    assert p["ubicacion_repartidor"] is None
    for privado in ("receptor_nombre", "receptor_documento", "firma", "usuario_id", "fecha_nacimiento"):
        assert privado not in str(publico)


@pytest.mark.parametrize(
    "cambio",
    [
        {"receptor_nombre": "  "},
        {"receptor_documento": ""},
        {"firma_base64": ""},
        {"firma_base64": base64.b64encode(b"<svg/>").decode()},
        {"receptor_fecha_nacimiento": "2030-01-01"},
        {"receptor_fecha_nacimiento": "1800-01-01"},
        {"es_autorizado": "true"},
        {"receptor_fecha_nacimiento": "2020-01-01"},
        {"created_at": "2020-01-01"},
    ],
)
async def test_hu12_rechaza_constancia_invalida_sin_cambios(client, db_session, administrativo_token, cambio):
    id_, paquetes, _, headers, _ = await _armar(client, db_session, administrativo_token)
    _olvidar_aviso_de_reparto(locals())
    resp = await client.post(
        f"{BASE}/{id_}/paquetes/{paquetes[0].id}/entrega", headers=headers, json=_constancia(**cambio)
    )
    assert resp.status_code == 400, resp.text
    assert await db_session.scalar(select(func.count()).select_from(EventoEntregaModel)) == 0
    await db_session.refresh(paquetes[0])
    assert paquetes[0].estado == "EN_REPARTO"


async def test_hu12_escenario_2_contacto_y_telefono_no_disponible(client, db_session, administrativo_token):
    id_, paquetes, _, headers, _ = await _armar(client, db_session, administrativo_token)
    _olvidar_aviso_de_reparto(locals())
    url = f"{BASE}/{id_}/paquetes/{paquetes[0].id}/contacto"
    datos = (await client.get(url, headers=headers)).json()["data"]
    assert datos["telefono"] == "+543564333444" and datos["telefono_disponible"]
    envio = await db_session.get(EnvioModel, paquetes[0].envio_id)
    envio.destinatario_telefono = "  "
    await db_session.commit()
    datos = (await client.get(url, headers=headers)).json()["data"]
    assert datos["telefono"] is None and not datos["telefono_disponible"]
    assert (await client.get(f"{BASE}/{id_}/paquetes/{uuid.uuid4()}/contacto", headers=headers)).status_code == 404


async def test_hu12_rechaza_entrega_en_larga_distancia(client, db_session, administrativo_token):
    id_, paquetes, _, headers, _ = await _armar(client, db_session, administrativo_token, tipo="LARGA")
    assert (
        await client.post(f"{BASE}/{id_}/paquetes/{paquetes[0].id}/entrega", headers=headers, json=_constancia())
    ).status_code == 400
    assert (await client.get(f"{BASE}/{id_}/paquetes/{paquetes[0].id}/contacto", headers=headers)).status_code == 400


async def test_hu12_escenario_3_visita_email_idempotente_y_seguimiento(
    client,
    db_session,
    administrativo_token,
    correo,
    whatsapp,
):
    id_, paquetes, usuario, headers, token = await _armar(client, db_session, administrativo_token, cantidad=1)
    _olvidar_aviso_de_reparto(locals())
    cuerpo = {"operacion_id": str(uuid.uuid4()), "motivo_fallo": "Persona ausente"}
    url = f"{BASE}/{id_}/paquetes/{paquetes[0].id}/visita-fallida"
    respuesta = await client.post(url, headers=headers, json=cuerpo)
    assert respuesta.status_code == 200, respuesta.text
    evento_id = respuesta.json()["data"]["evento_id"]
    assert len(correo.mensajes_enviados) == 1
    mensaje = correo.mensajes_enviados[0]
    assert mensaje["destinatario"] == "destino@test.com"
    assert "Aviso de visita" in mensaje["asunto"]
    assert token in mensaje["cuerpo_texto"]
    assert (await client.post(url, headers=headers, json=cuerpo)).json() == respuesta.json()
    assert len(correo.mensajes_enviados) == 1
    await db_session.refresh(paquetes[0])
    assert paquetes[0].estado == "ENTREGA_FALLIDA"
    evento = await db_session.get(EventoEntregaModel, uuid.UUID(evento_id))
    assert evento.motivo_fallo == "Persona ausente" and evento.usuario_registro_id == usuario.id
    aviso = (await db_session.scalars(select(NotificacionEnvioModel).where(NotificacionEnvioModel.canal == "EMAIL", NotificacionEnvioModel.tipo_aviso == "VISITA_FALLIDA"))).one()
    assert aviso.canal == "EMAIL" and aviso.estado == "ENVIADO"
    assert aviso.proveedor_mensaje_id and aviso.error_detalle is None
    assert str(aviso.evento_entrega_id) == evento_id
    # HU12 Escenario 3: el aviso también sale por WhatsApp, una sola vez, sin el motivo libre.
    assert len(whatsapp.mensajes_enviados) == 1
    mensaje_wa = whatsapp.mensajes_enviados[0]
    assert mensaje_wa["destinatario"] == "5493564333444"
    assert token in mensaje_wa["texto"] and "Persona ausente" not in mensaje_wa["texto"]
    aviso_wa = (
        await db_session.scalars(select(NotificacionEnvioModel).where(NotificacionEnvioModel.canal == "WHATSAPP", NotificacionEnvioModel.tipo_aviso == "VISITA_FALLIDA"))
    ).one()
    assert aviso_wa.estado == "ENVIADO" and str(aviso_wa.evento_entrega_id) == evento_id
    publico =(await client.get(f"/api/v1/seguimiento/{token}")).json()["data"]["paquetes"][0]
    assert publico["historial"][-1]["estado"] == "ENTREGA_FALLIDA"
    assert "Aviso de visita" in publico["historial"][-1]["descripcion"]
    assert "Persona ausente" not in str(publico)
    assert (
        await client.post(url, headers=headers, json={**cuerpo, "operacion_id": str(uuid.uuid4())})
    ).status_code == 409
    assert (await client.get(f"{BASE}/{id_}", headers=headers)).json()["data"]["estado"] == "FINALIZADO"


@pytest.mark.parametrize("excepcion", [False, True])
async def test_hu12_error_proveedor_conserva_visita_y_reintenta_solo_aviso_fallido(
    client,
    db_session,
    administrativo_token,
    correo,
    monkeypatch,
    excepcion,
):
    id_, paquetes, _, headers, _ = await _armar(client, db_session, administrativo_token)
    _olvidar_aviso_de_reparto(locals())
    if excepcion:

        async def fallar(**kwargs):
            raise RuntimeError("credencial-secreta")

        monkeypatch.setattr(correo, "enviar_email", fallar)
    else:
        correo.forzar_error = True
    cuerpo = {"operacion_id": str(uuid.uuid4()), "motivo_fallo": "No responde"}
    url = f"{BASE}/{id_}/paquetes/{paquetes[0].id}/visita-fallida"
    resp = await client.post(url, headers=headers, json=cuerpo)
    assert resp.status_code == 200, resp.text
    aviso = (await db_session.scalars(select(NotificacionEnvioModel).where(NotificacionEnvioModel.canal == "EMAIL", NotificacionEnvioModel.tipo_aviso == "VISITA_FALLIDA"))).one()
    await db_session.refresh(aviso)
    assert aviso.estado == "FALLIDO" and aviso.proveedor_mensaje_id is None
    assert "credencial-secreta" not in aviso.error_detalle
    await db_session.refresh(paquetes[0])
    assert paquetes[0].estado == "ENTREGA_FALLIDA"
    bueno = MockEmailProvider()
    monkeypatch.setattr(email_provider, "_email_provider_instance", bueno)
    repetida = await client.post(url, headers=headers, json=cuerpo)
    assert repetida.status_code == 200
    assert repetida.json() == resp.json()
    assert len(bueno.mensajes_enviados) == 1
    await db_session.refresh(aviso)
    assert aviso.estado == "ENVIADO" and aviso.error_detalle is None
    assert await db_session.scalar(select(func.count()).select_from(EventoEntregaModel)) == 1


async def test_hu12_reserva_notificacion_impide_despachos_duplicados(client, db_session, administrativo_token, correo):
    id_, paquetes, _, headers, _ = await _armar(client, db_session, administrativo_token)
    _olvidar_aviso_de_reparto(locals())
    resp = await client.post(
        f"{BASE}/{id_}/paquetes/{paquetes[0].id}/visita-fallida",
        headers=headers,
        json={"operacion_id": str(uuid.uuid4()), "motivo_fallo": "No responde"},
    )
    evento_id = uuid.UUID(resp.json()["data"]["evento_id"])
    servicio = ServicioNotificaciones(correo, session_factory=TestingSessionLocal)
    await servicio.notificar_visita_fallida(evento_id)
    await servicio.notificar_visita_fallida(evento_id)
    assert len(correo.mensajes_enviados) == 1


async def test_hu11_perfil_inactivo_no_expone_ubicacion(client, db_session, administrativo_token):
    id_, _, usuario, headers, token = await _armar(client, db_session, administrativo_token)
    _olvidar_aviso_de_reparto(locals())
    await client.put(f"{BASE}/{id_}/ubicacion", headers=headers, json={"latitud": 0, "longitud": 0})
    perfil = await db_session.get(RepartidorModel, usuario.id)
    perfil.activo = False
    await db_session.commit()
    assert (await client.get(f"{BASE}/{id_}", headers=headers)).status_code == 403
    publico = (await client.get(f"/api/v1/seguimiento/{token}")).json()["data"]["paquetes"]
    assert all(p["ubicacion_repartidor"] is None for p in publico)


@pytest.mark.parametrize("tipo", ["entrega", "visita-fallida"])
async def test_hu12_rollback_si_no_se_puede_confirmar_constancia(
    client,
    db_session,
    administrativo_token,
    monkeypatch,
    correo,
    tipo,
):
    id_, paquetes, _, headers, _ = await _armar(client, db_session, administrativo_token)
    _olvidar_aviso_de_reparto(locals())
    paquete_id = paquetes[0].id

    async def sesion_con_rollback():
        try:
            yield db_session
        except Exception:
            await db_session.rollback()
            raise

    async def fallo_commit(self):
        await self.db.flush()
        raise RuntimeError("Fallo simulado al confirmar")

    app.dependency_overrides[obtener_sesion_db] = sesion_con_rollback
    monkeypatch.setattr(RepositorioRecorridos, "confirmar", fallo_commit)
    cuerpo = _constancia() if tipo == "entrega" else {"operacion_id": str(uuid.uuid4()), "motivo_fallo": "Ausente"}
    with pytest.raises(RuntimeError, match="Fallo simulado"):
        await client.post(f"{BASE}/{id_}/paquetes/{paquete_id}/{tipo}", headers=headers, json=cuerpo)
    assert await db_session.scalar(select(PaqueteModel.estado).where(PaqueteModel.id == paquete_id)) == "EN_REPARTO"
    assert await db_session.scalar(select(func.count()).select_from(EventoEntregaModel)) == 0
    assert await db_session.scalar(
        select(func.count()).select_from(NotificacionEnvioModel).where(NotificacionEnvioModel.tipo_aviso != "EN_REPARTO")
    ) == 0
    assert (
        await db_session.scalar(
            select(func.count())
            .select_from(HistorialEstadoPaqueteModel)
            .where(
                HistorialEstadoPaqueteModel.estado_nuevo.in_(["ENTREGADO", "ENTREGA_FALLIDA"]),
            )
        )
        == 0
    )
    assert correo.mensajes_enviados == []


@pytest.mark.parametrize("radio,esperado", [(10.0, 1), (10.00001, 0), (9.99999, 1)])
async def test_hu11_limite_de_proximidad_10_km(client, db_session, administrativo_token, monkeypatch, radio, esperado):
    id_, _, _, headers, _ = await _armar(client, db_session, administrativo_token, tipo="LARGA", cantidad=1)
    monkeypatch.setattr("app.application.services.servicio_reparto.distancia_haversine_km", lambda *_: radio)
    resp = await client.put(f"{BASE}/{id_}/ubicacion", headers=headers, json={"latitud": -32.94, "longitud": -60.69})
    assert resp.status_code == 200, resp.text
    assert len(resp.json()["paquetes_actualizados"]) == esperado


async def test_hu12_sin_email_registra_fallo_y_conserva_visita(client, db_session, administrativo_token, correo):
    id_, paquetes, _, headers, _ = await _armar(client, db_session, administrativo_token)
    _olvidar_aviso_de_reparto(locals())
    envio = await db_session.get(EnvioModel, paquetes[0].envio_id)
    envio.destinatario_email = ""
    await db_session.commit()
    resp = await client.post(
        f"{BASE}/{id_}/paquetes/{paquetes[0].id}/visita-fallida",
        headers=headers,
        json={"operacion_id": str(uuid.uuid4()), "motivo_fallo": "No responde"},
    )
    assert resp.status_code == 200, resp.text
    aviso = (await db_session.scalars(select(NotificacionEnvioModel).where(NotificacionEnvioModel.canal == "EMAIL", NotificacionEnvioModel.tipo_aviso == "VISITA_FALLIDA"))).one()
    assert aviso.estado == "FALLIDO" and aviso.error_detalle
    assert not correo.mensajes_enviados


async def test_hu12_operacion_id_no_puede_reutilizarse_para_otro_paquete(client, db_session, administrativo_token):
    id_, paquetes, _, headers, _ = await _armar(client, db_session, administrativo_token)
    _olvidar_aviso_de_reparto(locals())
    cuerpo = _constancia()
    assert (
        await client.post(f"{BASE}/{id_}/paquetes/{paquetes[0].id}/entrega", headers=headers, json=cuerpo)
    ).status_code == 200
    resp = await client.post(f"{BASE}/{id_}/paquetes/{paquetes[1].id}/entrega", headers=headers, json=cuerpo)
    assert resp.status_code == 409
    await db_session.refresh(paquetes[1])
    assert paquetes[1].estado == "EN_REPARTO"


async def test_hu11_hu12_flujo_http_desde_registro_hasta_entrega(
    client,
    administrativo_token,
    vendedor_token,
    repartidor_usuario,
    correo,
):
    from tests.integration.test_flujo_punta_a_punta import _envio_a_domicilio

    admin = {"Authorization": f"Bearer {administrativo_token}"}
    vendedor = {"Authorization": f"Bearer {vendedor_token}"}
    registro = await client.post("/api/v1/envios", json=_envio_a_domicilio("San Martín 100", -31.41, -64.19))
    assert registro.status_code == 201, registro.text
    envio = registro.json()["data"]
    numero = envio["paquetes"][0]["numero_paquete"]
    recepcion = await client.post(
        f"/api/v1/terminal/paquetes/{numero}/recepcionar", headers=vendedor, json={"sucursal_id": 1}
    )
    assert recepcion.status_code == 200, recepcion.text
    perfil = await client.put(
        f"/api/v1/repartidores/{repartidor_usuario.id}/perfil",
        headers=admin,
        json={"sucursal_base_id": 1, "tipo_reparto": "CORTA", "activo": True},
    )
    assert perfil.status_code == 200, perfil.text
    recorrido = (await _generar(client, administrativo_token))["data"]["recorridos"][0]
    headers = _headers(repartidor_usuario)
    base = f"{BASE}/{recorrido['id']}"
    assert (await client.post(base + "/iniciar", headers=headers)).status_code == 200
    assert (
        await client.put(base + "/ubicacion", headers=headers, json={"latitud": -31.41, "longitud": -64.19})
    ).status_code == 200
    entrega = await client.post(
        base + f"/paquetes/{numero}/entrega",
        headers=headers,
        json=_constancia(receptor_nombre="María Gómez", es_autorizado=False),
    )
    assert entrega.status_code == 200, entrega.text
    publico = await client.get(f"/api/v1/seguimiento/{envio['token_seguimiento']}")
    paquete = publico.json()["data"]["paquetes"][0]
    assert paquete["estado"] == "ENTREGADO"
    assert [h["estado"] for h in paquete["historial"]] == ["EN_SUCURSAL_ORIGEN", "EN_REPARTO", "ENTREGADO"]
    assert paquete["ubicacion_repartidor"] is None
    assert (await client.get(base, headers=headers)).json()["data"]["estado"] == "FINALIZADO"


async def test_optimizar_en_reparto_desde_la_ubicacion_del_repartidor(client, db_session, administrativo_token):
    """El repartidor reordena lo que falta desde donde está; lo ya entregado no se mueve."""
    db_session.autoflush = False
    usuario = await _crear_repartidor(db_session, "Repartidor optimiza")
    puntos = {"oeste": (-31.41, -64.25), "centro": (-31.41, -64.19), "este": (-31.41, -64.13)}
    codigos = {}
    for nombre, (lat, lon) in puntos.items():
        [paquete] = await _crear_paquete(db_session, latitud=lat, longitud=lon)
        codigos[paquete.numero_paquete] = nombre
    id_ = (await _generar(client, administrativo_token))["data"]["recorridos"][0]["id"]
    headers = _headers(usuario)
    assert (await client.post(f"{BASE}/{id_}/iniciar", headers=headers)).status_code == 200

    # La primera parada ya se entregó.
    detalle = (await client.get(f"{BASE}/{id_}", headers=headers)).json()["data"]
    primera = detalle["paradas"][0]["paquetes"][0]["numero_paquete"]
    filas = (await db_session.execute(select(RecorridoPaqueteModel).where(RecorridoPaqueteModel.recorrido_id == uuid.UUID(id_)))).scalars().all()
    for fila in filas:
        if fila.orden == 1:
            fila.estado_en_recorrido = "ENTREGADO"
    await db_session.commit()

    # Está en el extremo este: lo pendiente arranca por lo más cercano a él.
    resp = await client.post(f"{BASE}/{id_}/optimizar", headers=headers, json={"latitud": -31.41, "longitud": -64.12})
    assert resp.status_code == 200, resp.text
    paradas = resp.json()["data"]["paradas"]
    orden = [p["paquetes"][0]["numero_paquete"] for p in paradas]
    assert orden[0] == primera, "lo entregado queda donde estaba"
    pendientes = [codigos[c] for c in orden[1:]]
    assert pendientes == sorted(pendientes, key=lambda n: -puntos[n][1]), "de este a oeste desde la posición"

    # Logística también puede optimizar un recorrido en reparto (desde la última posición conocida).
    admin = await client.post(f"/api/v1/recorridos/{id_}/optimizar", headers={"Authorization": f"Bearer {administrativo_token}"})
    assert admin.status_code == 200, admin.text
