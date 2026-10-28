import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

from app.application.interfaces.repositorio_recorridos import IRepositorioRecorridos
from app.application.interfaces.repositorio_sucursales import IRepositorioSucursales
from app.application.interfaces.servicio_recorridos import IServicioRecorridos
from app.application.interfaces.servicio_rutas import IServicioRutas
from app.contracts.recorridos import (
    TIPOS_DISTANCIA_VALIDOS,
    AlertaRecorridoData,
    AlertaRecorridoResponse,
    CompletarUbicacionPaqueteRequest,
    ControlCargaResumenData,
    CrearRecorridoRequest,
    EliminarRecorridoResponse,
    EsperaSucursalData,
    GeneracionRecorridosData,
    GenerarRecorridosRequest,
    GenerarRecorridosResponse,
    ListarAlertasRecorridoResponse,
    ListarRecorridosResponse,
    PaquetePendienteData,
    PaqueteRecorridoData,
    PaquetesPendientesResponse,
    ParadaRecorridoData,
    PuntoMapaData,
    ReasignarRepartidorRequest,
    RecorridoDetalleData,
    RecorridoResponse,
    RecorridoResumenData,
    ReemplazarPaquetesRecorridoRequest,
    RepartidorRecorridoData,
    ResumenEsperaData,
    ResumenEsperaResponse,
    ResumenGeneracionData,
)
from app.contracts.sucursales import SucursalData
from app.core.config import settings
from app.core.exceptions import DuplicateEntryException, NotFoundException, ValidationException
from app.domain.constants.estados_logistica import (
    EstadoRecorridoEnum,
    EstadoRecorridoPaqueteEnum,
    MotivoAlertaRecorridoEnum,
    TipoDistanciaEnum,
)
from app.domain.rules.destino_rules import formatear_destino_domicilio, formatear_destino_sucursal
from app.domain.rules.recepcion_rules import normalizar_codigo_escaneado
from app.domain.rules.recorrido_rules import (
    DESCRIPCIONES_MOTIVO_ALERTA,
    ESTADOS_RECORRIDO_EDITABLES,
    MINUTOS_POR_PARADA_DOMICILIO,
    MINUTOS_POR_PARADA_SUCURSAL,
    ParadaPlanificable,
    Punto,
    SucursalUbicada,
    determinar_tipo_reparto,
    elegir_sucursal_de_entrega,
    estado_paquete_al_iniciar,
    estimar_recorrido,
    funcion_distancia,
    misma_ciudad,
    ordenar_paradas,
    paquete_listo_para_despacho,
    repartir_paradas_equitativamente,
    vuelve_a_la_sucursal,
)
from app.domain.rules.retiro_rules import TIPO_ENTREGA_DOMICILIO, TIPO_ENTREGA_SUCURSAL
from app.infrastructure.db.models import (
    AlertaRecorridoModel,
    HistorialEstadoPaqueteModel,
    PaqueteModel,
    RecorridoModel,
    RecorridoPaqueteModel,
    SucursalModel,
)

TIPO_PARADA_DOMICILIO = "DOMICILIO"
TIPO_PARADA_SUCURSAL = "SUCURSAL"
ESTADOS_RECORRIDO_VALIDOS = [e.value for e in EstadoRecorridoEnum]


@dataclass(frozen=True)
class _DestinoReparto:
    """A dónde tiene que llevar el repartidor un paquete en un recorrido de cierto tipo."""

    clave: str
    tipo_parada: str
    texto: str
    punto: Punto | None
    sucursal: SucursalModel | None
    motivo_no_planificable: str | None = None


@dataclass
class _Clasificacion:
    """Paquetes listos para despacho en una sucursal, separados por tipo de reparto."""

    ids_por_tipo: dict[str, set[uuid.UUID]] = field(
        default_factory=lambda: {t: set() for t in TIPOS_DISTANCIA_VALIDOS}
    )
    pendientes: dict[str, list[PaqueteModel]] = field(
        default_factory=lambda: {t: [] for t in TIPOS_DISTANCIA_VALIDOS}
    )
    asignados: dict[uuid.UUID, uuid.UUID] = field(default_factory=dict)


def _otro_tipo(tipo_distancia: str) -> str:
    if tipo_distancia == TipoDistanciaEnum.CORTA.value:
        return TipoDistanciaEnum.LARGA.value
    return TipoDistanciaEnum.CORTA.value


def _agrupar_consecutivos[T](items: Iterable[T], clave: Callable[[T], str]) -> list[list[T]]:
    """Agrupa elementos consecutivos con la misma clave (paquetes de una misma parada)."""
    grupos: list[list[T]] = []
    clave_anterior: str | None = None
    for item in items:
        clave_actual = clave(item)
        if grupos and clave_actual == clave_anterior:
            grupos[-1].append(item)
        else:
            grupos.append([item])
        clave_anterior = clave_actual
    return grupos


class ServicioRecorridos(IServicioRecorridos):
    """Servicio de aplicación de los recorridos de reparto (HU10).

    - Escenario 1: `generar` clasifica los paquetes listos de la sucursal,
      arma las paradas y delega el reparto equitativo y el orden de visita en
      `domain/rules/recorrido_rules.py`.
    - Escenario 2: `obtener` devuelve el recorrido listo para un mapa;
      `reemplazar_paquetes`, `quitar_paquete`, `optimizar` y
      `reasignar_repartidor` son la edición manual.
    - Escenario 3: al terminar cualquier generación o edición se sincronizan
      las alertas de paquetes que quedaron sin recorrido.
    - Escenario 4: el tipo de cada paquete (corta o larga distancia) se decide
      por la sucursal que atiende su destino.
    """

    def __init__(
        self,
        repositorio_recorridos: IRepositorioRecorridos,
        repositorio_sucursales: IRepositorioSucursales,
        rutas: IServicioRutas | None = None,
    ):
        self.rutas = rutas
        """Tiempos reales de manejo por calles (OSRM). Sin él, se estima por distancia."""
        self.repo = repositorio_recorridos
        self.repo_sucursales = repositorio_sucursales

    # ------------------------------------------------------------------
    # Escenario 1: generación automática
    # ------------------------------------------------------------------

    async def generar(self, datos: GenerarRecorridosRequest, usuario: Any) -> GenerarRecorridosResponse:
        fecha = datos.fecha or date.today()
        tipo = datos.tipo_distancia
        orientacion = datos.orientacion_calles_grados
        sucursal = await self._obtener_sucursal_origen(datos.sucursal_id)
        origen = self._punto_sucursal(sucursal)

        # Sin `reemplazar_existentes`, lo ya armado se respeta: se reparte solo lo que no tiene
        # recorrido, entre los repartidores que todavía están libres ese día.
        existentes = (
            await self.repo.listar_recorridos_editables(sucursal.id, fecha, tipo) if datos.reemplazar_existentes else []
        )
        ids_reemplazo = {r.id for r in existentes}

        repartidores = await self._repartidores_para_generar(
            sucursal.id, tipo, fecha, datos.repartidor_ids, ids_reemplazo
        )
        sucursales = await self.repo_sucursales.listar_todas()
        clasificacion = await self._clasificar(sucursal, sucursales, excluir_recorridos=ids_reemplazo)
        candidatos = clasificacion.pendientes[tipo]

        paradas, paquetes_por_clave, sin_asignar = self._armar_paradas(candidatos, tipo, sucursal, sucursales)

        for recorrido in existentes:
            await self.repo.eliminar(recorrido)
        await self.repo.sincronizar()

        ids_generados: list[uuid.UUID] = []
        if paradas and repartidores:
            grupos = [
                await self._ordenar(origen, grupo, tipo, orientacion) if grupo else []
                for grupo in repartir_paradas_equitativamente(origen, paradas, len(repartidores))
            ]
            for repartidor, grupo in zip(repartidores, grupos, strict=True):
                if not grupo:
                    continue
                recorrido = RecorridoModel(
                    id=uuid.uuid4(),
                    repartidor_id=repartidor.usuario_id,
                    sucursal_origen_id=sucursal.id,
                    tipo_distancia=tipo,
                    fecha=fecha,
                    estado=EstadoRecorridoEnum.GENERADO.value,
                    generado_automaticamente=True,
                    orientacion_calles_grados=orientacion,
                )
                paquetes = [p for parada in grupo for p in paquetes_por_clave[parada.clave]]
                for orden, paquete in enumerate(paquetes, start=1):
                    recorrido.paquetes.append(RecorridoPaqueteModel(paquete_id=paquete.id, orden=orden))
                recorrido.distancia_estimada_km, recorrido.duracion_estimada_min = await self._estimar_paradas(
                    origen, grupo, tipo, orientacion
                )
                await self.repo.agregar(recorrido)
                ids_generados.append(recorrido.id)
        elif paradas:
            for paquetes in paquetes_por_clave.values():
                for paquete in paquetes:
                    sin_asignar[paquete.id] = MotivoAlertaRecorridoEnum.SIN_REPARTIDOR_DISPONIBLE.value

        await self.repo.sincronizar()
        await self._sincronizar_alertas(
            sucursal.id, clasificacion.ids_por_tipo[_otro_tipo(tipo)], sin_asignar, recorrido_id=None
        )
        await self.repo.confirmar()

        recorridos = [await self._detalle(id_, sucursales) for id_ in ids_generados]
        alertas = await self._alertas_de_paquetes(list(sin_asignar))
        asignados = sum(r.cantidad_paquetes for r in recorridos)

        mensaje = f"Se generaron {len(recorridos)} recorrido(s) con {asignados} paquete(s)."
        if not candidatos:
            mensaje = "No hay paquetes esperando un recorrido de este tipo en la sucursal."
        elif not repartidores:
            mensaje = "No hay repartidores libres para ese día: todos ya tienen recorrido o no están activos."
        if sin_asignar:
            mensaje += f" {len(sin_asignar)} paquete(s) quedaron sin recorrido: revisá las alertas."

        return GenerarRecorridosResponse(
            message=mensaje,
            data=GeneracionRecorridosData(
                sucursal_id=sucursal.id,
                fecha=fecha,
                tipo_distancia=tipo,
                orientacion_calles_grados=orientacion,
                resumen=ResumenGeneracionData(
                    paquetes_pendientes=len(candidatos),
                    paquetes_asignados=asignados,
                    paquetes_sin_recorrido=len(sin_asignar),
                    repartidores_disponibles=len(repartidores),
                    recorridos_generados=len(recorridos),
                    recorridos_reemplazados=len(existentes),
                ),
                recorridos=recorridos,
                alertas=alertas,
            ),
        )

    # ------------------------------------------------------------------
    # Escenario 2: visualización
    # ------------------------------------------------------------------

    async def listar(
        self,
        sucursal_id: int | None = None,
        fecha: date | None = None,
        tipo_distancia: str | None = None,
        estado: str | None = None,
        repartidor_id: uuid.UUID | None = None,
        desde: date | None = None,
        hasta: date | None = None,
    ) -> ListarRecorridosResponse:
        tipo = tipo_distancia.strip().upper() if tipo_distancia and tipo_distancia.strip() else None
        estado_filtro = estado.strip().upper() if estado and estado.strip() else None
        errores = []
        if tipo and tipo not in TIPOS_DISTANCIA_VALIDOS:
            errores.append({"field": "tipo_distancia", "message": f"Tipo de distancia inválido: '{tipo_distancia}'."})
        if estado_filtro and estado_filtro not in ESTADOS_RECORRIDO_VALIDOS:
            errores.append({"field": "estado", "message": f"Estado de recorrido inválido: '{estado}'."})
        if errores:
            raise ValidationException(message="Los filtros indicados no son válidos.", errors=errores)

        recorridos = await self.repo.listar_recorridos(
            sucursal_id=sucursal_id,
            fecha=fecha,
            tipo_distancia=tipo,
            estado=estado_filtro,
            repartidor_id=repartidor_id,
            desde=desde,
            hasta=hasta,
        )
        sucursales = await self.repo_sucursales.listar_todas()
        return ListarRecorridosResponse(
            total=len(recorridos),
            data=[self._mapear_resumen(r, sucursales) for r in recorridos],
        )

    async def obtener(self, id: uuid.UUID) -> RecorridoResponse:
        await self._obtener_recorrido(id)
        sucursales = await self.repo_sucursales.listar_todas()
        return RecorridoResponse(data=await self._detalle(id, sucursales))

    # ------------------------------------------------------------------
    # Escenario 2: edición manual
    # ------------------------------------------------------------------

    async def crear(self, datos: CrearRecorridoRequest) -> RecorridoResponse:
        fecha = datos.fecha or date.today()
        sucursal = await self._obtener_sucursal_origen(datos.sucursal_id)
        # Valida que el repartidor sea de esta sucursal y tipo, y que esté libre ese día.
        await self._repartidores_para_generar(sucursal.id, datos.tipo_distancia, fecha, [datos.repartidor_id], set())
        sucursales = await self.repo_sucursales.listar_todas()
        recorrido = RecorridoModel(
            id=uuid.uuid4(),
            repartidor_id=datos.repartidor_id,
            sucursal_origen_id=sucursal.id,
            tipo_distancia=datos.tipo_distancia,
            fecha=fecha,
            estado=EstadoRecorridoEnum.EN_EDICION.value,
            generado_automaticamente=False,
            orientacion_calles_grados=0.0,
        )
        recorrido.sucursal_origen = sucursal
        recorrido.paquetes = []  # colección ya cargada: así no se consulta en diferido después de guardar
        ordenados = await self._paquetes_validos(recorrido, sucursal, sucursales, datos.paquetes)
        await self.repo.agregar(recorrido)
        await self.repo.sincronizar()
        alertas = await self._aplicar_composicion(recorrido, ordenados, sucursales, edicion_manual=True)
        return RecorridoResponse(
            message=f"Recorrido creado con {len(ordenados)} paquete(s).",
            data=await self._detalle(recorrido.id, sucursales),
            alertas=alertas,
        )

    async def resumen_espera(self) -> ResumenEsperaResponse:
        sucursales = await self.repo_sucursales.listar_todas()
        por_sucursal = []
        for sucursal in sucursales:
            clasificacion = await self._clasificar(sucursal, sucursales)
            corta = len(clasificacion.pendientes[TipoDistanciaEnum.CORTA.value])
            larga = len(clasificacion.pendientes[TipoDistanciaEnum.LARGA.value])
            if corta or larga:
                por_sucursal.append(EsperaSucursalData(
                    sucursal_id=sucursal.id, nombre=sucursal.nombre, a_domicilio=corta, entre_sucursales=larga,
                ))
        por_sucursal.sort(key=lambda s: -(s.a_domicilio + s.entre_sucursales))
        return ResumenEsperaResponse(data=ResumenEsperaData(
            sin_llegar=await self.repo.contar_sin_llegar(), sucursales=por_sucursal,
        ))

    async def pendientes(self, sucursal_id: int, tipo_distancia: str) -> PaquetesPendientesResponse:
        tipo = tipo_distancia.strip().upper()
        if tipo not in TIPOS_DISTANCIA_VALIDOS:
            raise ValidationException(
                message="El tipo de distancia no es válido.",
                errors=[{"field": "tipo_distancia", "message": "Usá CORTA o LARGA."}],
            )
        sucursal = await self._obtener_sucursal_origen(sucursal_id)
        sucursales = await self.repo_sucursales.listar_todas()
        clasificacion = await self._clasificar(sucursal, sucursales)
        paquetes = clasificacion.pendientes[tipo]
        visitas = await self.repo.visitas_fallidas_de([p.id for p in paquetes])
        datos = []
        for paquete in paquetes:
            destino = self._destino(paquete, tipo, sucursal, sucursales)
            motivo = destino.motivo_no_planificable
            datos.append(PaquetePendienteData(
                paquete_id=paquete.id,
                numero_paquete=paquete.numero_paquete,
                descripcion=paquete.descripcion,
                peso_kg=paquete.peso_kg,
                destinatario_nombre=paquete.envio.destinatario_nombre,
                destino=destino.texto,
                token_seguimiento=paquete.envio.token_seguimiento,
                tiene_ubicacion=destino.punto is not None,
                motivo=DESCRIPCIONES_MOTIVO_ALERTA.get(motivo, motivo) if motivo else None,
                visitas_previas=visitas.get(paquete.id, 0),
                en_devolucion=bool(paquete.en_devolucion),
            ))
        return PaquetesPendientesResponse(total=len(datos), data=datos)

    async def reemplazar_paquetes(
        self, id: uuid.UUID, datos: ReemplazarPaquetesRecorridoRequest
    ) -> RecorridoResponse:
        recorrido = await self._obtener_editable(id)
        sucursal = recorrido.sucursal_origen
        sucursales = await self.repo_sucursales.listar_todas()
        ordenados = await self._paquetes_validos(recorrido, sucursal, sucursales, datos.paquetes)
        alertas = await self._aplicar_composicion(recorrido, ordenados, sucursales, edicion_manual=True)
        return RecorridoResponse(
            message="Recorrido actualizado manualmente.",
            data=await self._detalle(recorrido.id, sucursales),
            alertas=alertas,
        )

    async def _paquetes_validos(
        self, recorrido: RecorridoModel, sucursal: SucursalModel, sucursales: list[SucursalModel], codigos_pedidos: list[str]
    ) -> list[PaqueteModel]:
        """Paquetes pedidos, en ese orden, si todos existen, no se repiten y pueden ir en este recorrido."""
        codigos = [normalizar_codigo_escaneado(c) for c in codigos_pedidos]
        paquetes_encontrados = await self.repo.buscar_paquetes_por_codigos(codigos)
        por_codigo: dict[str, PaqueteModel] = {}
        for paquete in paquetes_encontrados:
            por_codigo[paquete.numero_paquete] = paquete
            por_codigo[str(paquete.id).upper()] = paquete

        errores = [
            {"field": f"paquetes[{i}]", "message": f"No existe un paquete con el código '{codigo}'."}
            for i, codigo in enumerate(codigos)
            if codigo not in por_codigo
        ]
        if errores:
            raise ValidationException(message="Hay paquetes que no existen.", errors=errores)

        ordenados = [por_codigo[c] for c in codigos]
        vistos: set[uuid.UUID] = set()
        for i, paquete in enumerate(ordenados):
            if paquete.id in vistos:
                errores.append({
                    "field": f"paquetes[{i}]",
                    "message": f"El paquete {paquete.numero_paquete} está repetido en la lista.",
                })
            vistos.add(paquete.id)
        if errores:
            raise ValidationException(message="La lista de paquetes tiene repetidos.", errors=errores)

        clasificacion = await self._clasificar(sucursal, sucursales, excluir_recorridos={recorrido.id})
        for i, paquete in enumerate(ordenados):
            motivo = self._motivo_no_asignable(paquete, recorrido, sucursal, clasificacion)
            if motivo:
                errores.append({"field": f"paquetes[{i}]", "message": motivo})
        if errores:
            raise ValidationException(
                message="Hay paquetes que no se pueden incluir en este recorrido.",
                errors=errores,
            )
        return ordenados

    async def quitar_paquete(self, id: uuid.UUID, codigo: str) -> RecorridoResponse:
        recorrido = await self._obtener_editable(id)
        sucursales = await self.repo_sucursales.listar_todas()
        objetivo = normalizar_codigo_escaneado(codigo)

        actuales = [rp.paquete for rp in sorted(recorrido.paquetes, key=lambda rp: rp.orden)]
        restantes = [p for p in actuales if objetivo not in (p.numero_paquete, str(p.id).upper())]
        if len(restantes) == len(actuales):
            raise NotFoundException(f"El paquete '{objetivo}' no forma parte de este recorrido.")
        if not restantes:
            raise ValidationException(
                message="No se puede quitar el último paquete del recorrido.",
                errors=[{"field": "codigo", "message": "Para descartar el recorrido completo, eliminalo."}],
            )

        alertas = await self._aplicar_composicion(recorrido, restantes, sucursales, edicion_manual=True)
        return RecorridoResponse(
            message="Paquete quitado del recorrido.",
            data=await self._detalle(recorrido.id, sucursales),
            alertas=alertas,
        )

    async def completar_ubicacion(
        self, id: uuid.UUID, codigo: str, datos: CompletarUbicacionPaqueteRequest
    ) -> RecorridoResponse:
        recorrido = await self._obtener_editable(id)
        objetivo = normalizar_codigo_escaneado(codigo)
        paquete = next(
            (rp.paquete for rp in recorrido.paquetes
             if objetivo in (rp.paquete.numero_paquete, str(rp.paquete.id).upper())),
            None,
        )
        if paquete is None:
            raise NotFoundException(f"El paquete '{objetivo}' no forma parte de este recorrido.")
        envio = paquete.envio
        if recorrido.tipo_distancia != TipoDistanciaEnum.CORTA.value or envio.tipo_entrega != TIPO_ENTREGA_DOMICILIO:
            raise ValidationException(message="Solo se puede ubicar un domicilio de un recorrido de corta distancia.")
        if envio.latitud_destino is not None and envio.longitud_destino is not None:
            raise DuplicateEntryException(message="El domicilio ya tiene ubicación. Actualizá el detalle del recorrido.")

        afectados = await self.repo.listar_recorridos_activos_del_envio(envio.id)
        if any(r.estado not in ESTADOS_RECORRIDO_EDITABLES for r in afectados):
            raise DuplicateEntryException(
                message="No se puede cambiar la ubicación: otro paquete del envío tiene un recorrido en curso."
            )
        sucursales = await self.repo_sucursales.listar_todas()
        ubicacion_anterior = (envio.latitud_destino, envio.longitud_destino)
        envio.latitud_destino = datos.latitud
        envio.longitud_destino = datos.longitud
        for actual in afectados:
            if any(
                rp.paquete.envio_id == envio.id
                and self._tipo_reparto(rp.paquete, actual.sucursal_origen, sucursales) != actual.tipo_distancia
                for rp in actual.paquetes
            ):
                envio.latitud_destino, envio.longitud_destino = ubicacion_anterior
                raise ValidationException(
                    message="La ubicación corresponde a otra sucursal de entrega. Revisá el punto seleccionado."
                )
        for actual in afectados:
            paquetes = [rp.paquete for rp in sorted(actual.paquetes, key=lambda rp: rp.orden)]
            actual.distancia_estimada_km, actual.duracion_estimada_min = await self._estimar(
                actual, paquetes, actual.sucursal_origen, sucursales
            )
            actual.estado = EstadoRecorridoEnum.EN_EDICION.value
            actual.generado_automaticamente = False

        await self.repo.sincronizar()
        pendientes: set[uuid.UUID] = set()
        contextos = {(r.sucursal_origen_id, r.tipo_distancia) for r in afectados}
        for sucursal_id, tipo in contextos:
            sucursal = next(s for s in sucursales if s.id == sucursal_id)
            sin_asignar, clasificacion = await self._pendientes_sin_recorrido(sucursal, tipo, sucursales)
            await self._sincronizar_alertas(
                sucursal_id, clasificacion.ids_por_tipo[_otro_tipo(tipo)], sin_asignar, recorrido.id
            )
            pendientes.update(sin_asignar)
        await self.repo.confirmar()
        return RecorridoResponse(
            message="Ubicación guardada. Se actualizaron las paradas y las estimaciones del recorrido.",
            data=await self._detalle(recorrido.id, sucursales),
            alertas=await self._alertas_de_paquetes(list(pendientes)),
        )

    async def optimizar(self, id: uuid.UUID, desde: Punto | None = None) -> RecorridoResponse:
        """Recalcula el orden de visita más rápido por calles (tiempos reales de OSRM).

        Antes de salir ordena todo desde la sucursal. En reparto reordena solo lo
        pendiente, desde `desde` (la ubicación del repartidor) o su última posición.
        """
        recorrido = await self._obtener_recorrido(id)
        if recorrido.estado == EstadoRecorridoEnum.EN_CURSO.value:
            return await self._optimizar_en_reparto(recorrido, desde)
        recorrido = await self._obtener_editable(id)
        sucursal = recorrido.sucursal_origen
        sucursales = await self.repo_sucursales.listar_todas()
        tipo = recorrido.tipo_distancia

        paquetes_por_clave: dict[str, list[PaqueteModel]] = {}
        planificables: dict[str, ParadaPlanificable] = {}
        sin_ubicacion: list[PaqueteModel] = []
        for rp in sorted(recorrido.paquetes, key=lambda rp: rp.orden):
            destino = self._destino(rp.paquete, tipo, sucursal, sucursales)
            if destino.punto is None:
                sin_ubicacion.append(rp.paquete)
                continue
            paquetes_por_clave.setdefault(destino.clave, []).append(rp.paquete)
            planificables[destino.clave] = ParadaPlanificable(
                destino.clave, destino.punto[0], destino.punto[1], len(paquetes_por_clave[destino.clave])
            )

        ordenadas = await self._ordenar(
            self._punto_sucursal(sucursal), list(planificables.values()), tipo, recorrido.orientacion_calles_grados
        )
        nuevo_orden = [p for parada in ordenadas for p in paquetes_por_clave[parada.clave]] + sin_ubicacion

        alertas = await self._aplicar_composicion(recorrido, nuevo_orden, sucursales, edicion_manual=False)
        return RecorridoResponse(
            message="Orden de visita optimizado.",
            data=await self._detalle(recorrido.id, sucursales),
            alertas=alertas,
        )

    async def _optimizar_en_reparto(self, recorrido: RecorridoModel, desde: Punto | None) -> RecorridoResponse:
        """Lo entregado o visitado queda como está; lo pendiente se ordena desde donde está el vehículo."""
        sucursal = recorrido.sucursal_origen
        sucursales = await self.repo_sucursales.listar_todas()
        tipo = recorrido.tipo_distancia
        if desde is None:
            posicion = await self.repo.obtener_posicion(recorrido.repartidor_id)
            if posicion is not None and posicion.recorrido_id == recorrido.id:
                desde = (posicion.latitud, posicion.longitud)
        desde = desde or self._punto_sucursal(sucursal)

        hechos: list[RecorridoPaqueteModel] = []
        por_clave: dict[str, list[RecorridoPaqueteModel]] = {}
        planificables: dict[str, ParadaPlanificable] = {}
        sin_ubicacion: list[RecorridoPaqueteModel] = []
        for rp in sorted(recorrido.paquetes, key=lambda rp: rp.orden):
            if rp.estado_en_recorrido != EstadoRecorridoPaqueteEnum.PENDIENTE.value:
                hechos.append(rp)
                continue
            destino = self._destino(rp.paquete, tipo, sucursal, sucursales)
            if destino.punto is None:
                sin_ubicacion.append(rp)
                continue
            por_clave.setdefault(destino.clave, []).append(rp)
            planificables[destino.clave] = ParadaPlanificable(
                destino.clave, destino.punto[0], destino.punto[1], len(por_clave[destino.clave])
            )
        if len(planificables) < 2:
            return RecorridoResponse(
                message="Queda una sola parada: no hay nada que reordenar.",
                data=await self._detalle(recorrido.id, sucursales),
            )

        # Desde el vehículo hacia lo que falta (sin volver: la vuelta la decide el repartidor).
        ordenadas = await self._ordenar(desde, list(planificables.values()), tipo, recorrido.orientacion_calles_grados, vuelve=False)
        nuevo = hechos + [rp for parada in ordenadas for rp in por_clave[parada.clave]] + sin_ubicacion
        # Dos pasos para no chocar con la restricción única (recorrido, orden).
        for indice, rp in enumerate(nuevo, start=1):
            rp.orden = 10_000 + indice
        await self.repo.sincronizar()
        for indice, rp in enumerate(nuevo, start=1):
            rp.orden = indice
        await self.repo.sincronizar()
        await self.repo.confirmar()
        return RecorridoResponse(
            message="Recorrido optimizado: las paradas pendientes quedaron en el orden más rápido desde la ubicación actual.",
            data=await self._detalle(recorrido.id, sucursales),
        )

    async def reasignar_repartidor(self, id: uuid.UUID, datos: ReasignarRepartidorRequest) -> RecorridoResponse:
        recorrido = await self._obtener_editable(id)
        sucursales = await self.repo_sucursales.listar_todas()

        repartidor = await self.repo.obtener_repartidor(datos.repartidor_id)
        motivo = self._motivo_repartidor_no_apto(
            repartidor, recorrido.sucursal_origen_id, recorrido.tipo_distancia
        )
        if motivo:
            raise ValidationException(
                message="El repartidor indicado no puede tomar este recorrido.",
                errors=[{"field": "repartidor_id", "message": motivo}],
            )

        if repartidor.usuario_id != recorrido.repartidor_id:
            ocupados = await self.repo.repartidores_con_recorrido_activo(
                recorrido.fecha, excluir_recorridos={recorrido.id}
            )
            if repartidor.usuario_id in ocupados:
                raise DuplicateEntryException(
                    message="El repartidor ya tiene otro recorrido activo para esa fecha.",
                    errors=[{"field": "repartidor_id", "message": "Repartidor ocupado."}],
                )
            recorrido.repartidor_id = repartidor.usuario_id
            recorrido.estado = EstadoRecorridoEnum.EN_EDICION.value
            recorrido.generado_automaticamente = False
            await self.repo.confirmar()

        return RecorridoResponse(
            message="Repartidor reasignado.",
            data=await self._detalle(recorrido.id, sucursales),
        )

    # ------------------------------------------------------------------
    # Salida del recorrido y descarte
    # ------------------------------------------------------------------

    async def iniciar(self, id: uuid.UUID, usuario: Any) -> RecorridoResponse:
        """Despacha el recorrido: pasa a `EN_CURSO` y sus paquetes salen de la sucursal.

        Cada paquete pasa a `EN_REPARTO` (corta distancia) o `EN_TRANSITO`
        (larga), deja de estar ubicado en la sucursal y suma una fila al
        historial de estados, todo en un solo commit. Desde ahí el recorrido
        es del repartidor (HU11) y ya no se edita.
        """
        recorrido = await self._obtener_recorrido(id)
        if recorrido.estado not in ESTADOS_RECORRIDO_EDITABLES:
            raise ValidationException(
                message="Solo se puede iniciar un recorrido generado o en edición.",
                errors=[{"field": "estado", "message": f"Estado actual del recorrido: '{recorrido.estado}'."}],
            )

        items = sorted(recorrido.paquetes, key=lambda rp: rp.orden)
        if not items:
            raise ValidationException(
                message="El recorrido no tiene paquetes.",
                errors=[{"field": "paquetes", "message": "Agregá paquetes antes de iniciarlo."}],
            )

        sucursal = recorrido.sucursal_origen
        errores = [
            {
                "field": "paquetes",
                "message": (
                    f"El paquete {rp.paquete.numero_paquete} ya no está listo en la sucursal "
                    f"(estado '{rp.paquete.estado}'). Quitalo del recorrido antes de iniciarlo."
                ),
            }
            for rp in items
            if rp.paquete.sucursal_actual_id != sucursal.id or not paquete_listo_para_despacho(rp.paquete.estado)
        ]
        if errores:
            raise ValidationException(message="Hay paquetes que no pueden salir en este recorrido.", errors=errores)

        nuevo_estado = estado_paquete_al_iniciar(recorrido.tipo_distancia)
        repartidor_nombre = recorrido.repartidor.usuario.nombre
        ahora = datetime.now(UTC)
        for rp in items:
            paquete = rp.paquete
            await self.repo.agregar(
                HistorialEstadoPaqueteModel(
                    paquete_id=paquete.id,
                    estado_anterior=paquete.estado,
                    estado_nuevo=nuevo_estado,
                    usuario_id=usuario.id,
                    sucursal_id=sucursal.id,
                    latitud=sucursal.latitud,
                    longitud=sucursal.longitud,
                    observacion=(
                        f"Salió de {sucursal.nombre} en un recorrido de {recorrido.tipo_distancia.lower()} "
                        f"distancia a cargo de {repartidor_nombre}."
                    ),
                    created_at=ahora,
                )
            )
            paquete.estado = nuevo_estado
            paquete.sucursal_actual_id = None

        recorrido.estado = EstadoRecorridoEnum.EN_CURSO.value

        for alerta in await self.repo.alertas_pendientes_de_paquetes([rp.paquete_id for rp in items]):
            alerta.resuelta = True
            alerta.resuelta_at = ahora
        await self.repo.confirmar()

        sucursales = await self.repo_sucursales.listar_todas()
        return RecorridoResponse(
            message=f"Recorrido iniciado: {len(items)} paquete(s) pasaron a {nuevo_estado}.",
            data=await self._detalle(recorrido.id, sucursales),
        )

    async def eliminar(self, id: uuid.UUID) -> EliminarRecorridoResponse:
        recorrido = await self._obtener_editable(id)
        sucursal = recorrido.sucursal_origen
        tipo = recorrido.tipo_distancia
        sucursales = await self.repo_sucursales.listar_todas()

        await self.repo.eliminar(recorrido)
        await self.repo.sincronizar()
        sin_asignar, clasificacion = await self._pendientes_sin_recorrido(sucursal, tipo, sucursales)
        await self._sincronizar_alertas(
            sucursal.id, clasificacion.ids_por_tipo[_otro_tipo(tipo)], sin_asignar, recorrido_id=None
        )
        await self.repo.confirmar()

        return EliminarRecorridoResponse(alertas=await self._alertas_de_paquetes(list(sin_asignar)))

    # ------------------------------------------------------------------
    # Escenario 3: alertas
    # ------------------------------------------------------------------

    async def listar_alertas(
        self,
        sucursal_id: int | None = None,
        incluir_resueltas: bool = False,
    ) -> ListarAlertasRecorridoResponse:
        alertas = await self.repo.listar_alertas(sucursal_id=sucursal_id, incluir_resueltas=incluir_resueltas)
        return ListarAlertasRecorridoResponse(total=len(alertas), data=[self._mapear_alerta(a) for a in alertas])

    async def resolver_alerta(self, id: uuid.UUID) -> AlertaRecorridoResponse:
        """Marca una alerta como atendida por fuera del sistema (por ejemplo, el
        paquete se entregó en mano). Si el paquete sigue sin recorrido, la
        próxima generación o edición la vuelve a crear."""
        alerta = await self.repo.obtener_alerta(id)
        if not alerta:
            raise NotFoundException(f"No existe una alerta con id {id}.")
        if alerta.resuelta:
            raise ValidationException(
                message="La alerta ya estaba resuelta.",
                errors=[{"field": "resuelta", "message": "La alerta ya fue resuelta anteriormente."}],
            )
        alerta.resuelta = True
        alerta.resuelta_at = datetime.now(UTC)
        await self.repo.confirmar()
        actualizada = await self.repo.obtener_alerta(id)
        return AlertaRecorridoResponse(message="Alerta marcada como resuelta.", data=self._mapear_alerta(actualizada))

    # ------------------------------------------------------------------
    # Auxiliares: clasificación y destinos
    # ------------------------------------------------------------------

    async def _obtener_sucursal_origen(self, sucursal_id: int) -> SucursalModel:
        sucursal = await self.repo_sucursales.obtener_por_id(sucursal_id)
        if not sucursal:
            raise ValidationException(
                message="La sucursal de partida no existe.",
                errors=[{"field": "sucursal_id", "message": f"No existe una sucursal con id {sucursal_id}."}],
            )
        if sucursal.latitud is None or sucursal.longitud is None:
            raise ValidationException(
                message="La sucursal de partida no tiene coordenadas.",
                errors=[{
                    "field": "sucursal_id",
                    "message": "Sin la ubicación de la sucursal no se pueden calcular los recorridos.",
                }],
            )
        return sucursal

    async def _repartidores_para_generar(
        self,
        sucursal_id: int,
        tipo: str,
        fecha: date,
        repartidor_ids: list[uuid.UUID] | None,
        ids_reemplazo: set[uuid.UUID],
    ) -> list[Any]:
        disponibles = await self.repo.listar_repartidores_disponibles(sucursal_id, tipo)
        ocupados = await self.repo.repartidores_con_recorrido_activo(fecha, excluir_recorridos=ids_reemplazo)

        if not repartidor_ids:
            return [r for r in disponibles if r.usuario_id not in ocupados]

        por_id = {r.usuario_id: r for r in disponibles}
        errores = []
        seleccion = []
        for i, repartidor_id in enumerate(dict.fromkeys(repartidor_ids)):
            if repartidor_id not in por_id:
                errores.append({
                    "field": f"repartidor_ids[{i}]",
                    "message": (
                        f"{repartidor_id} no es un repartidor activo de {tipo.lower()} distancia con base en "
                        "esta sucursal."
                    ),
                })
            elif repartidor_id in ocupados:
                errores.append({
                    "field": f"repartidor_ids[{i}]",
                    "message": f"{repartidor_id} ya tiene un recorrido activo para esa fecha.",
                })
            else:
                seleccion.append(por_id[repartidor_id])
        if errores:
            raise ValidationException(message="Hay repartidores que no pueden recibir recorridos.", errors=errores)
        return seleccion

    def _motivo_repartidor_no_apto(self, repartidor: Any, sucursal_id: int, tipo: str) -> str | None:
        if not repartidor:
            return "No existe un perfil de repartidor para ese usuario."
        if not repartidor.activo or repartidor.usuario.estado != "Activo":
            return "El repartidor no está activo."
        if repartidor.sucursal_base_id != sucursal_id:
            return "El repartidor tiene base en otra sucursal."
        if repartidor.tipo_reparto != tipo:
            return f"El repartidor hace recorridos de {repartidor.tipo_reparto.lower()} distancia."
        return None

    async def _clasificar(
        self,
        sucursal: SucursalModel,
        sucursales: list[SucursalModel],
        excluir_recorridos: set[uuid.UUID] | None = None,
    ) -> _Clasificacion:
        """Separa por tipo de reparto los paquetes listos en la sucursal y marca
        cuáles ya están en un recorrido activo."""
        clasificacion = _Clasificacion()
        paquetes = await self.repo.listar_paquetes_listos_en_sucursal(sucursal.id)
        clasificacion.asignados = await self.repo.paquetes_en_recorridos_activos(excluir_recorridos)

        for paquete in paquetes:
            tipo = self._tipo_reparto(paquete, sucursal, sucursales)
            if not tipo:
                continue
            clasificacion.ids_por_tipo[tipo].add(paquete.id)
            if paquete.id not in clasificacion.asignados:
                clasificacion.pendientes[tipo].append(paquete)
        return clasificacion

    def _sucursal_entrega_id(
        self, envio: Any, sucursal_actual_id: int, sucursales: list[SucursalModel], paquete: Any | None = None
    ) -> int | None:
        # Una devolución vuelve a la sucursal donde se admitió el paquete.
        if paquete is not None and getattr(paquete, "en_devolucion", False):
            return paquete.sucursal_origen_id
        if (envio.tipo_entrega or "").strip().lower() == TIPO_ENTREGA_SUCURSAL:
            return envio.sucursal_destino_id
        punto = None
        if envio.latitud_destino is not None and envio.longitud_destino is not None:
            punto = (envio.latitud_destino, envio.longitud_destino)
        return elegir_sucursal_de_entrega(
            envio.ciudad_destino,
            envio.provincia_destino,
            punto,
            [SucursalUbicada(s.id, s.ciudad, s.provincia, s.latitud, s.longitud) for s in sucursales],
            sucursal_actual_id=sucursal_actual_id,
        )

    def _tipo_reparto(self, paquete: PaqueteModel, sucursal: SucursalModel, sucursales: list[SucursalModel]) -> str | None:
        envio = paquete.envio
        if paquete.en_devolucion:
            origen = paquete.sucursal_origen_id
            return TipoDistanciaEnum.LARGA.value if origen and origen != sucursal.id else None
        return determinar_tipo_reparto(
            envio.tipo_entrega,
            self._sucursal_entrega_id(envio, sucursal.id, sucursales),
            sucursal.id,
            misma_ciudad(envio.ciudad_destino, envio.provincia_destino, sucursal.ciudad, sucursal.provincia),
        )

    def _destino(
        self,
        paquete: PaqueteModel,
        tipo: str,
        sucursal: SucursalModel,
        sucursales: list[SucursalModel],
    ) -> _DestinoReparto:
        """Parada a la que va el paquete: su domicilio (corta) o la sucursal de entrega (larga)."""
        envio = paquete.envio
        if tipo == TipoDistanciaEnum.CORTA.value:
            texto = self._texto_destino_final(envio)
            if (envio.tipo_entrega or "").strip().lower() == TIPO_ENTREGA_DOMICILIO and (
                envio.latitud_destino is not None and envio.longitud_destino is not None
            ):
                punto = (envio.latitud_destino, envio.longitud_destino)
                return _DestinoReparto(
                    clave=f"D:{punto[0]:.5f},{punto[1]:.5f}",
                    tipo_parada=TIPO_PARADA_DOMICILIO,
                    texto=texto,
                    punto=punto,
                    sucursal=None,
                )
            return _DestinoReparto(
                clave=f"D:SIN-UBICACION:{paquete.id}",
                tipo_parada=TIPO_PARADA_DOMICILIO,
                texto=texto,
                punto=None,
                sucursal=None,
                motivo_no_planificable=MotivoAlertaRecorridoEnum.SIN_UBICACION_DESTINO.value,
            )

        entrega_id = self._sucursal_entrega_id(envio, sucursal.id, sucursales, paquete)
        destino_sucursal = next((s for s in sucursales if s.id == entrega_id), None)
        if not destino_sucursal:
            return _DestinoReparto(
                clave=f"S:SIN-SUCURSAL:{paquete.id}",
                tipo_parada=TIPO_PARADA_SUCURSAL,
                texto="Sucursal de destino no determinada",
                punto=None,
                sucursal=None,
                motivo_no_planificable=MotivoAlertaRecorridoEnum.SIN_SUCURSAL_DESTINO.value,
            )
        punto = self._punto_sucursal(destino_sucursal)
        return _DestinoReparto(
            clave=f"S:{destino_sucursal.id}",
            tipo_parada=TIPO_PARADA_SUCURSAL,
            texto=formatear_destino_sucursal(
                nombre=destino_sucursal.nombre,
                direccion=destino_sucursal.direccion,
                ciudad=destino_sucursal.ciudad,
                provincia=destino_sucursal.provincia,
            ),
            punto=punto,
            sucursal=destino_sucursal,
            motivo_no_planificable=None if punto else MotivoAlertaRecorridoEnum.SIN_UBICACION_DESTINO.value,
        )

    def _armar_paradas(
        self,
        paquetes: list[PaqueteModel],
        tipo: str,
        sucursal: SucursalModel,
        sucursales: list[SucursalModel],
    ) -> tuple[list[ParadaPlanificable], dict[str, list[PaqueteModel]], dict[uuid.UUID, str]]:
        """Agrupa los paquetes en paradas planificables. Los que no se pueden
        ubicar en el mapa quedan en `sin_asignar` con su motivo de alerta."""
        paquetes_por_clave: dict[str, list[PaqueteModel]] = {}
        puntos: dict[str, Punto] = {}
        sin_asignar: dict[uuid.UUID, str] = {}

        for paquete in paquetes:
            destino = self._destino(paquete, tipo, sucursal, sucursales)
            if destino.motivo_no_planificable or destino.punto is None:
                sin_asignar[paquete.id] = destino.motivo_no_planificable or (
                    MotivoAlertaRecorridoEnum.SIN_UBICACION_DESTINO.value
                )
                continue
            paquetes_por_clave.setdefault(destino.clave, []).append(paquete)
            puntos[destino.clave] = destino.punto

        paradas = [
            ParadaPlanificable(clave, puntos[clave][0], puntos[clave][1], len(paquetes_clave))
            for clave, paquetes_clave in paquetes_por_clave.items()
        ]
        return paradas, paquetes_por_clave, sin_asignar

    def _motivo_no_asignable(
        self,
        paquete: PaqueteModel,
        recorrido: RecorridoModel,
        sucursal: SucursalModel,
        clasificacion: _Clasificacion,
    ) -> str | None:
        tipo = recorrido.tipo_distancia
        if paquete.sucursal_actual_id != sucursal.id:
            return f"El paquete {paquete.numero_paquete} no está en la sucursal de partida del recorrido."
        if not paquete_listo_para_despacho(paquete.estado):
            return f"El paquete {paquete.numero_paquete} está en estado '{paquete.estado}' y no puede despacharse."
        if paquete.id in clasificacion.asignados:
            return f"El paquete {paquete.numero_paquete} ya está asignado a otro recorrido activo."
        if paquete.id in clasificacion.ids_por_tipo[_otro_tipo(tipo)]:
            return (
                f"El paquete {paquete.numero_paquete} necesita un recorrido de "
                f"{_otro_tipo(tipo).lower()} distancia."
            )
        if paquete.id not in clasificacion.ids_por_tipo[tipo]:
            return f"El paquete {paquete.numero_paquete} ya está en su sucursal de retiro: no necesita reparto."
        return None

    # ------------------------------------------------------------------
    # Auxiliares: composición, estimación y alertas
    # ------------------------------------------------------------------

    async def _aplicar_composicion(
        self,
        recorrido: RecorridoModel,
        paquetes: list[PaqueteModel],
        sucursales: list[SucursalModel],
        edicion_manual: bool,
    ) -> list[AlertaRecorridoData]:
        """Reemplaza los paquetes del recorrido por `paquetes` en ese orden,
        recalcula las estimaciones y sincroniza las alertas (Escenario 3)."""
        sucursal = recorrido.sucursal_origen

        # Primero se borran las filas viejas: si se insertaran en el mismo flush,
        # chocarían con las restricciones únicas (recorrido, orden) y (recorrido, paquete).
        recorrido.paquetes.clear()
        await self.repo.sincronizar()
        for orden, paquete in enumerate(paquetes, start=1):
            recorrido.paquetes.append(RecorridoPaqueteModel(paquete_id=paquete.id, orden=orden))

        recorrido.distancia_estimada_km, recorrido.duracion_estimada_min = await self._estimar(
            recorrido, paquetes, sucursal, sucursales
        )
        if edicion_manual:
            recorrido.estado = EstadoRecorridoEnum.EN_EDICION.value
            recorrido.generado_automaticamente = False
        await self.repo.sincronizar()

        sin_asignar, clasificacion = await self._pendientes_sin_recorrido(
            sucursal, recorrido.tipo_distancia, sucursales
        )
        await self._sincronizar_alertas(
            sucursal.id,
            clasificacion.ids_por_tipo[_otro_tipo(recorrido.tipo_distancia)],
            sin_asignar,
            recorrido_id=recorrido.id,
        )
        await self.repo.confirmar()
        return await self._alertas_de_paquetes(list(sin_asignar))

    async def _ordenar(
        self, origen: Punto | None, paradas: list[ParadaPlanificable], tipo: str, orientacion: float,
        vuelve: bool | None = None,
    ) -> list[ParadaPlanificable]:
        """El orden de visita que menos tarda: vecino más cercano + 2-opt sobre los tiempos
        reales de manejo por calles (OSRM). Sin OSRM, sobre la distancia estimada."""
        vuelve = vuelve_a_la_sucursal(tipo) if vuelve is None else vuelve
        respaldo = funcion_distancia(tipo, orientacion)
        if origen is None or len(paradas) < 2 or self.rutas is None:
            return ordenar_paradas(origen, paradas, respaldo, vuelve) if origen else list(paradas)
        puntos = list(dict.fromkeys([origen, *(p.punto for p in paradas)]))
        matriz = await self.rutas.matriz(puntos)
        if matriz is None:
            return ordenar_paradas(origen, paradas, respaldo, vuelve)
        indice = {punto: i for i, punto in enumerate(puntos)}
        return ordenar_paradas(origen, paradas, lambda a, b: matriz[indice[a]][indice[b]], vuelve)

    async def _estimar_paradas(
        self, origen: Punto | None, paradas: list[ParadaPlanificable], tipo: str, orientacion: float,
        paradas_sin_ubicacion: int = 0,
    ) -> tuple[float, int]:
        """Kilómetros y minutos del recorrido en ese orden: por calles (OSRM) más la atención en cada parada."""
        if origen is not None and paradas and self.rutas is not None:
            puntos = [origen, *(p.punto for p in paradas), *([origen] if vuelve_a_la_sucursal(tipo) else [])]
            real = await self.rutas.recorrido(puntos)
            if real is not None:
                metros, segundos = real
                por_parada = MINUTOS_POR_PARADA_DOMICILIO if tipo == TipoDistanciaEnum.CORTA.value else MINUTOS_POR_PARADA_SUCURSAL
                minutos = segundos / 60 + (len(paradas) + paradas_sin_ubicacion) * por_parada
                return round(metros / 1000, 2), int(round(minutos))
        if origen is None:
            return 0.0, 0
        return estimar_recorrido(origen, paradas, tipo, orientacion, paradas_sin_ubicacion=paradas_sin_ubicacion)

    async def _estimar(
        self,
        recorrido: RecorridoModel,
        paquetes: list[PaqueteModel],
        sucursal: SucursalModel,
        sucursales: list[SucursalModel],
    ) -> tuple[float, int]:
        destinos = [self._destino(p, recorrido.tipo_distancia, sucursal, sucursales) for p in paquetes]
        grupos = _agrupar_consecutivos(destinos, lambda d: d.clave)
        planificables = [
            ParadaPlanificable(grupo[0].clave, grupo[0].punto[0], grupo[0].punto[1], len(grupo))
            for grupo in grupos
            if grupo[0].punto is not None
        ]
        sin_ubicacion = sum(1 for grupo in grupos if grupo[0].punto is None)
        return await self._estimar_paradas(
            self._punto_sucursal(sucursal), planificables, recorrido.tipo_distancia,
            recorrido.orientacion_calles_grados, paradas_sin_ubicacion=sin_ubicacion,
        )

    async def _pendientes_sin_recorrido(
        self,
        sucursal: SucursalModel,
        tipo: str,
        sucursales: list[SucursalModel],
    ) -> tuple[dict[uuid.UUID, str], _Clasificacion]:
        """Paquetes de la sucursal que necesitan un recorrido de este tipo y no tienen ninguno."""
        clasificacion = await self._clasificar(sucursal, sucursales)
        sin_asignar = {
            paquete.id: (
                self._destino(paquete, tipo, sucursal, sucursales).motivo_no_planificable
                or MotivoAlertaRecorridoEnum.SIN_RECORRIDO_ASIGNADO.value
            )
            for paquete in clasificacion.pendientes[tipo]
        }
        return sin_asignar, clasificacion

    async def _sincronizar_alertas(
        self,
        sucursal_id: int,
        ids_otro_tipo: set[uuid.UUID],
        sin_asignar: dict[uuid.UUID, str],
        recorrido_id: uuid.UUID | None,
    ) -> None:
        """Deja una alerta pendiente por cada paquete sin recorrido (HU10 Escenario 3).

        - Paquete que sigue sin recorrido: se conserva su alerta (actualizando el
          motivo si cambió) o se crea una nueva.
        - Paquete que ya tiene recorrido o dejó de necesitarlo: se resuelve.
        - Paquete que corresponde al otro tipo de reparto: no se toca, lo
          sincroniza la generación/edición de ese tipo.
        """
        ahora = datetime.now(UTC)
        pendientes = await self.repo.listar_alertas_pendientes_en_sucursal(sucursal_id)
        con_alerta: set[uuid.UUID] = set()

        for alerta in pendientes:
            if alerta.paquete_id in sin_asignar:
                con_alerta.add(alerta.paquete_id)
                if alerta.motivo != sin_asignar[alerta.paquete_id]:
                    alerta.motivo = sin_asignar[alerta.paquete_id]
                    alerta.recorrido_id = recorrido_id
            elif alerta.paquete_id not in ids_otro_tipo:
                alerta.resuelta = True
                alerta.resuelta_at = ahora

        for paquete_id, motivo in sin_asignar.items():
            if paquete_id not in con_alerta:
                await self.repo.agregar(
                    AlertaRecorridoModel(
                        id=uuid.uuid4(),
                        paquete_id=paquete_id,
                        recorrido_id=recorrido_id,
                        motivo=motivo,
                        resuelta=False,
                    )
                )
        await self.repo.sincronizar()

    async def _alertas_de_paquetes(self, paquete_ids: list[uuid.UUID]) -> list[AlertaRecorridoData]:
        alertas = await self.repo.alertas_pendientes_de_paquetes(paquete_ids)
        return [self._mapear_alerta(a) for a in alertas]

    # ------------------------------------------------------------------
    # Auxiliares: lectura y mapeo
    # ------------------------------------------------------------------

    async def _obtener_recorrido(self, id: uuid.UUID) -> RecorridoModel:
        recorrido = await self.repo.obtener_recorrido(id)
        if not recorrido:
            raise NotFoundException(f"No existe un recorrido con id {id}.")
        return recorrido

    async def _obtener_editable(self, id: uuid.UUID) -> RecorridoModel:
        recorrido = await self._obtener_recorrido(id)
        if recorrido.estado not in ESTADOS_RECORRIDO_EDITABLES:
            raise ValidationException(
                message="El recorrido ya no se puede editar.",
                errors=[{
                    "field": "estado",
                    "message": (
                        f"Solo se editan recorridos generados o en edición. Estado actual: '{recorrido.estado}'."
                    ),
                }],
            )
        return recorrido

    async def _detalle(self, id: uuid.UUID, sucursales: list[SucursalModel]) -> RecorridoDetalleData:
        recorrido = await self._obtener_recorrido(id)
        detalle = self._mapear_detalle(recorrido, sucursales)
        visitas = await self.repo.visitas_fallidas_de([rp.paquete_id for rp in recorrido.paquetes])
        for parada in detalle.paradas:
            for paquete in parada.paquetes:
                paquete.visitas_previas = visitas.get(paquete.paquete_id, 0)
        carga = await self.repo.control_de_carga(recorrido.id)
        if carga is not None:
            estado, verificados = carga
            detalle.control_carga = ControlCargaResumenData(
                estado=estado, verificados=verificados, esperados=len(recorrido.paquetes)
            )
        detalle.max_visitas = settings.MAX_VISITAS_DOMICILIO
        return detalle

    def _punto_sucursal(self, sucursal: SucursalModel) -> Punto | None:
        if sucursal.latitud is None or sucursal.longitud is None:
            return None
        return (sucursal.latitud, sucursal.longitud)

    def _texto_destino_final(self, envio: Any) -> str:
        if (envio.tipo_entrega or "").strip().lower() == TIPO_ENTREGA_DOMICILIO:
            return formatear_destino_domicilio(
                direccion=envio.direccion_destino,
                ciudad=envio.ciudad_destino,
                provincia=envio.provincia_destino,
            )
        sucursal = envio.sucursal_destino
        return formatear_destino_sucursal(
            nombre=sucursal.nombre if sucursal else None,
            direccion=sucursal.direccion if sucursal else None,
            ciudad=sucursal.ciudad if sucursal else None,
            provincia=sucursal.provincia if sucursal else None,
        )

    def _mapear_sucursal(self, sucursal: SucursalModel | None) -> SucursalData | None:
        if not sucursal:
            return None
        return SucursalData(
            id=sucursal.id,
            nombre=sucursal.nombre,
            provincia=sucursal.provincia,
            ciudad=sucursal.ciudad,
            direccion=sucursal.direccion,
            latitud=sucursal.latitud,
            longitud=sucursal.longitud,
        )

    async def paradas_en_sucursales(
        self, recorrido: RecorridoModel
    ) -> list[tuple[SucursalModel, list[RecorridoPaqueteModel]]]:
        sucursales = await self.repo_sucursales.listar_todas()
        return [
            (destino.sucursal, grupo)
            for destino, grupo in self._paradas(recorrido, sucursales)
            if destino.sucursal is not None
        ]

    async def paquetes_que_bajan_en(
        self, recorridos: list[RecorridoModel], sucursal_id: int
    ) -> dict[uuid.UUID, list[RecorridoPaqueteModel]]:
        sucursales = await self.repo_sucursales.listar_todas()
        return {
            recorrido.id: [
                rp
                for destino, grupo in self._paradas(recorrido, sucursales)
                if destino.sucursal is not None and destino.sucursal.id == sucursal_id
                for rp in grupo
            ]
            for recorrido in recorridos
        }

    def _paradas(
        self, recorrido: RecorridoModel, sucursales: list[SucursalModel]
    ) -> list[tuple[_DestinoReparto, list[RecorridoPaqueteModel]]]:
        items = sorted(recorrido.paquetes, key=lambda rp: rp.orden)
        con_destino = [
            (self._destino(rp.paquete, recorrido.tipo_distancia, recorrido.sucursal_origen, sucursales), rp)
            for rp in items
        ]
        grupos = _agrupar_consecutivos(con_destino, lambda par: par[0].clave)
        return [(grupo[0][0], [rp for _, rp in grupo]) for grupo in grupos]

    def _mapear_resumen(self, recorrido: RecorridoModel, sucursales: list[SucursalModel]) -> RecorridoResumenData:
        usuario = recorrido.repartidor.usuario
        return RecorridoResumenData(
            id=recorrido.id,
            fecha=recorrido.fecha,
            tipo_distancia=recorrido.tipo_distancia,
            estado=recorrido.estado,
            generado_automaticamente=recorrido.generado_automaticamente,
            sucursal_origen_id=recorrido.sucursal_origen_id,
            sucursal_origen_nombre=recorrido.sucursal_origen.nombre,
            repartidor=RepartidorRecorridoData(usuario_id=usuario.id, nombre=usuario.nombre, telefono=usuario.telefono),
            cantidad_paradas=len(self._paradas(recorrido, sucursales)),
            cantidad_paquetes=len(recorrido.paquetes),
            paquetes_entregados=sum(
                1 for rp in recorrido.paquetes if rp.estado_en_recorrido == EstadoRecorridoPaqueteEnum.ENTREGADO.value
            ),
            paquetes_no_entregados=sum(
                1 for rp in recorrido.paquetes if rp.estado_en_recorrido == EstadoRecorridoPaqueteEnum.FALLIDO.value
            ),
            distancia_estimada_km=recorrido.distancia_estimada_km,
            duracion_estimada_min=recorrido.duracion_estimada_min,
            created_at=recorrido.created_at,
            updated_at=recorrido.updated_at,
        )

    def _mapear_detalle(self, recorrido: RecorridoModel, sucursales: list[SucursalModel]) -> RecorridoDetalleData:
        paradas = self._paradas(recorrido, sucursales)
        origen = self._punto_sucursal(recorrido.sucursal_origen)
        vuelve = vuelve_a_la_sucursal(recorrido.tipo_distancia)

        trazado: list[PuntoMapaData] = []
        if origen:
            trazado.append(PuntoMapaData(latitud=origen[0], longitud=origen[1]))
        trazado.extend(
            PuntoMapaData(latitud=destino.punto[0], longitud=destino.punto[1])
            for destino, _ in paradas
            if destino.punto is not None
        )
        if origen and vuelve and len(trazado) > 1:
            trazado.append(PuntoMapaData(latitud=origen[0], longitud=origen[1]))

        resumen = self._mapear_resumen(recorrido, sucursales)
        return RecorridoDetalleData(
            **resumen.model_dump(),
            orientacion_calles_grados=recorrido.orientacion_calles_grados,
            vuelve_a_sucursal=vuelve,
            sucursal_origen=self._mapear_sucursal(recorrido.sucursal_origen),
            paradas=[
                ParadaRecorridoData(
                    orden=indice,
                    tipo_parada=destino.tipo_parada,
                    destino=destino.texto,
                    latitud=destino.punto[0] if destino.punto else None,
                    longitud=destino.punto[1] if destino.punto else None,
                    sucursal_destino=self._mapear_sucursal(destino.sucursal),
                    paquetes=[
                        PaqueteRecorridoData(
                            paquete_id=rp.paquete.id,
                            numero_paquete=rp.paquete.numero_paquete,
                            orden=rp.orden,
                            descripcion=rp.paquete.descripcion,
                            peso_kg=rp.paquete.peso_kg,
                            estado=rp.paquete.estado,
                            estado_en_recorrido=rp.estado_en_recorrido,
                            token_seguimiento=rp.paquete.envio.token_seguimiento,
                            destinatario_nombre=rp.paquete.envio.destinatario_nombre,
                            destinatario_telefono=rp.paquete.envio.destinatario_telefono,
                            en_devolucion=rp.paquete.en_devolucion,
                        )
                        for rp in items
                    ],
                )
                for indice, (destino, items) in enumerate(paradas, start=1)
            ],
            trazado=trazado,
            paquetes_sin_ubicacion=sum(len(items) for destino, items in paradas if destino.punto is None),
        )

    def _mapear_alerta(self, alerta: AlertaRecorridoModel) -> AlertaRecorridoData:
        paquete = alerta.paquete
        return AlertaRecorridoData(
            id=alerta.id,
            paquete_id=alerta.paquete_id,
            numero_paquete=paquete.numero_paquete,
            token_seguimiento=paquete.envio.token_seguimiento,
            destino=self._texto_destino_final(paquete.envio),
            motivo=alerta.motivo,
            descripcion_motivo=DESCRIPCIONES_MOTIVO_ALERTA.get(alerta.motivo, alerta.motivo),
            sucursal_actual_id=paquete.sucursal_actual_id,
            recorrido_id=alerta.recorrido_id,
            resuelta=alerta.resuelta,
            created_at=alerta.created_at,
            resuelta_at=alerta.resuelta_at,
        )
