"""Solicitudes simultáneas con sesiones distintas y SQLite en disco, sin StaticPool."""

import asyncio
import uuid
from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.application.services.servicio_notificaciones import ServicioNotificaciones
from app.application.services.servicio_recorridos import ServicioRecorridos
from app.application.services.servicio_reparto import ServicioReparto
from app.contracts.reparto import RegistrarEntregaRequest, RegistrarVisitaFallidaRequest
from app.core.exceptions import DuplicateEntryException
from app.infrastructure.db.models import (
    Base,
    EventoEntregaModel,
    HistorialEstadoPaqueteModel,
    NotificacionEnvioModel,
    RecorridoModel,
    RecorridoPaqueteModel,
    RolModel,
    SucursalModel,
    UsuarioModel,
)
from app.infrastructure.repositories.repositorio_entregas import RepositorioEntregas
from app.infrastructure.repositories.repositorio_recorridos import RepositorioRecorridos
from app.infrastructure.repositories.repositorio_sucursales import RepositorioSucursales
from tests.integration.test_hu10_recorridos import _crear_paquete, _crear_repartidor
from tests.integration.test_hu11_hu12_reparto import _constancia


def _servicio(sesion):
    repo = RepositorioRecorridos(sesion)
    return ServicioReparto(repo, RepositorioEntregas(sesion), ServicioRecorridos(repo, RepositorioSucursales(sesion)))


@pytest_asyncio.fixture
async def reparto_en_disco(tmp_path):
    ruta = (tmp_path / "concurrencia.db").as_posix()
    engine = create_async_engine(f"sqlite+aiosqlite:///{ruta}", connect_args={"timeout": 10})
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    try:
        async with engine.begin() as conexion:
            await conexion.run_sync(Base.metadata.create_all)
        async with factory() as sesion:
            sesion.add(RolModel(id=4, nombre="REPARTIDOR", descripcion="Repartidor"))
            sesion.add(
                SucursalModel(
                    id=1,
                    nombre="Centro",
                    ciudad="Córdoba",
                    provincia="Córdoba",
                    direccion="Centro 123",
                    latitud=-31.4,
                    longitud=-64.18,
                )
            )
            await sesion.commit()
            usuario = await _crear_repartidor(sesion, "Concurrente")
            paquete = (await _crear_paquete(sesion, latitud=-31.41, longitud=-64.19))[0]
            paquete.estado = "EN_REPARTO"
            paquete.sucursal_actual_id = None
            recorrido = RecorridoModel(
                id=uuid.uuid4(),
                repartidor_id=usuario.id,
                sucursal_origen_id=1,
                tipo_distancia="CORTA",
                estado="EN_CURSO",
                fecha=date.today(),
            )
            recorrido.paquetes = [
                RecorridoPaqueteModel(paquete_id=paquete.id, orden=1, estado_en_recorrido="PENDIENTE")
            ]
            sesion.add(recorrido)
            await sesion.commit()
            yield factory, recorrido.id, paquete.id, usuario.id
    finally:
        await engine.dispose()


@pytest.mark.parametrize("misma_operacion", [True, False])
async def test_hu12_entregas_simultaneas_solo_generan_una_constancia(reparto_en_disco, misma_operacion):
    factory, recorrido_id, paquete_id, usuario_id = reparto_en_disco
    cuerpo = _constancia()
    datos = [
        RegistrarEntregaRequest(**cuerpo),
        RegistrarEntregaRequest(
            **{
                **cuerpo,
                "operacion_id": cuerpo["operacion_id"] if misma_operacion else str(uuid.uuid4()),
            }
        ),
    ]

    async def entregar(solicitud):
        async with factory() as sesion:
            try:
                usuario = await sesion.get(UsuarioModel, usuario_id)
                return await _servicio(sesion).registrar_entrega(recorrido_id, str(paquete_id), solicitud, usuario)
            except DuplicateEntryException as exc:
                await sesion.rollback()
                return exc

    respuestas = await asyncio.gather(*(entregar(solicitud) for solicitud in datos))
    exitosas = [r for r in respuestas if not isinstance(r, Exception)]
    assert len(exitosas) == (2 if misma_operacion else 1)
    assert len({r.data.evento_id for r in exitosas}) == 1
    if not misma_operacion:
        assert any(isinstance(r, DuplicateEntryException) for r in respuestas)
    async with factory() as sesion:
        assert await sesion.scalar(select(func.count()).select_from(EventoEntregaModel)) == 1
        assert await sesion.scalar(select(func.count()).select_from(HistorialEstadoPaqueteModel)) == 1


async def test_hu12_aviso_simultaneo_se_reserva_una_sola_vez(reparto_en_disco):
    factory, recorrido_id, paquete_id, usuario_id = reparto_en_disco
    async with factory() as sesion:
        usuario = await sesion.get(UsuarioModel, usuario_id)
        evento = await _servicio(sesion).registrar_visita_fallida(
            recorrido_id,
            str(paquete_id),
            RegistrarVisitaFallidaRequest(operacion_id=uuid.uuid4(), motivo_fallo="Ausente"),
            usuario,
        )
    iniciado, continuar = asyncio.Event(), asyncio.Event()

    class ProveedorLento:
        llamadas = 0

        async def enviar_email(self, **kwargs):
            self.llamadas += 1
            iniciado.set()
            await continuar.wait()
            return True, "id-proveedor", None

    proveedor = ProveedorLento()
    servicio = ServicioNotificaciones(proveedor, session_factory=factory)
    primera = asyncio.create_task(servicio.notificar_visita_fallida(evento.data.evento_id))
    try:
        await asyncio.wait_for(iniciado.wait(), timeout=5)
        await servicio.notificar_visita_fallida(evento.data.evento_id)
        assert proveedor.llamadas == 1
    finally:
        continuar.set()
        await primera
    async with factory() as sesion:
        aviso = (await sesion.scalars(select(NotificacionEnvioModel))).one()
        assert aviso.estado == "ENVIADO" and aviso.proveedor_mensaje_id == "id-proveedor"
