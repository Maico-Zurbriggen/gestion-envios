"""Control de descarga en la sucursal de destino.

Un recorrido de larga distancia sale de una sucursal y deja paquetes en otras.
Al llegar, el personal de cada sucursal de destino escanea lo que baja del
vehículo: cada lectura se compara con lo que ese recorrido tenía que dejar ahí.
Al cerrar el control, lo que no apareció queda como alerta de faltante.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from app.application.interfaces.repositorio_descargas import IRepositorioDescargas
from app.application.interfaces.servicio_recorridos import IServicioRecorridos
from app.contracts.descargas import (
    CerrarControlRequest,
    ControlDescargaData,
    ControlDescargaResponse,
    IniciarControlRequest,
    LecturaDescargaData,
    PaqueteEsperadoData,
    RecorridoDescargaData,
    RecorridoEntranteData,
    RecorridosEntrantesResponse,
    RegistrarLecturaRequest,
    ResultadoLecturaData,
    ResultadoLecturaResponse,
    SucursalDescargaData,
)
from app.core.exceptions import NotFoundException, ValidationException
from app.domain.constants.estados_logistica import (
    EstadoPaqueteEnum,
    EstadoRecorridoEnum,
    EstadoRecorridoPaqueteEnum,
    MotivoAlertaRecorridoEnum,
    TipoDistanciaEnum,
)
from app.domain.rules.descarga_rules import (
    CERRADO,
    CORRECTO,
    DESCONOCIDO,
    DIAS_RECORRIDOS_ENTRANTES,
    EN_CURSO,
    ESTADOS_RECORRIDO_CONTROLABLES,
    SOBRANTE,
    es_codigo_de_paquete,
    motivo_sobrante,
    normalizar_codigo,
    resumen_control,
)
from app.domain.rules.monitor_rules import etiqueta_estado
from app.infrastructure.db.models import (
    AlertaRecorridoModel,
    ControlDescargaModel,
    HistorialEstadoPaqueteModel,
    LecturaDescargaModel,
)


def _nombre(usuario: Any) -> str | None:
    return getattr(usuario, "nombre", None) if usuario else None


class ServicioDescargas:
    def __init__(self, repositorio: IRepositorioDescargas, servicio_recorridos: IServicioRecorridos):
        self.repo = repositorio
        self.recorridos = servicio_recorridos

    async def _paradas_en(self, recorrido_id: uuid.UUID, sucursal_id: int) -> list[Any]:
        """Paquetes que el recorrido tiene que dejar en la sucursal (según sus paradas)."""
        detalle = (await self.recorridos.obtener(recorrido_id)).data
        return [
            paquete
            for parada in detalle.paradas
            if parada.sucursal_destino is not None and parada.sucursal_destino.id == sucursal_id
            for paquete in parada.paquetes
        ]

    # --- Recorridos que llegan a una sucursal --------------------------------

    async def recorridos_entrantes(self, sucursal_id: int, hoy: datetime | None = None) -> RecorridosEntrantesResponse:
        if await self.repo.obtener_sucursal(sucursal_id) is None:
            raise NotFoundException("No existe esa sucursal.")
        hoy = hoy or datetime.now(UTC)
        desde = (hoy - timedelta(days=DIAS_RECORRIDOS_ENTRANTES)).date()
        recorridos = await self.repo.recorridos_larga_desde(desde, ESTADOS_RECORRIDO_CONTROLABLES)
        controles = await self.repo.controles_de_sucursal(sucursal_id, [r.id for r in recorridos])
        entrantes = []
        for recorrido in recorridos:
            if recorrido.sucursal_origen_id == sucursal_id:
                continue
            esperados = await self._paradas_en(recorrido.id, sucursal_id)
            if not esperados:
                continue
            control = controles.get(recorrido.id)
            ids = {p.paquete_id for p in esperados}
            verificados = (
                sum(1 for lectura in control.lecturas if lectura.resultado == CORRECTO and lectura.paquete_id in ids)
                if control
                else 0
            )
            entrantes.append(RecorridoEntranteData(
                recorrido_id=recorrido.id,
                fecha=recorrido.fecha,
                estado=recorrido.estado,
                repartidor_nombre=_nombre(recorrido.repartidor.usuario) or "Repartidor",
                sucursal_origen=recorrido.sucursal_origen.nombre,
                esperados=len(esperados),
                verificados=verificados,
                control_id=control.id if control else None,
                control_estado=control.estado if control else None,
            ))
        return RecorridosEntrantesResponse(data=entrantes)

    # --- Control ------------------------------------------------------------

    async def iniciar(self, datos: IniciarControlRequest, usuario: Any) -> ControlDescargaResponse:
        existente = await self.repo.obtener_control_por(datos.recorrido_id, datos.sucursal_id)
        if existente:
            return ControlDescargaResponse(data=await self._dato(existente))
        recorrido = await self.repo.obtener_recorrido(datos.recorrido_id)
        if recorrido is None:
            raise NotFoundException("No existe ese recorrido.")
        if await self.repo.obtener_sucursal(datos.sucursal_id) is None:
            raise NotFoundException("No existe esa sucursal.")
        if recorrido.tipo_distancia != TipoDistanciaEnum.LARGA.value:
            raise ValidationException(
                message="Solo se controla la descarga de recorridos de larga distancia.",
                errors=[{"field": "recorrido_id", "message": "El recorrido es de corta distancia: entrega en domicilios."}],
            )
        if recorrido.estado not in ESTADOS_RECORRIDO_CONTROLABLES:
            raise ValidationException(
                message="El recorrido todavía no salió de su sucursal.",
                errors=[{"field": "recorrido_id", "message": "Se puede controlar cuando el repartidor inicia el recorrido."}],
            )
        if not await self._paradas_en(recorrido.id, datos.sucursal_id):
            raise ValidationException(
                message="Este recorrido no deja paquetes en esa sucursal.",
                errors=[{"field": "sucursal_id", "message": "Elegí la sucursal donde descarga el recorrido."}],
            )
        control = ControlDescargaModel(
            id=uuid.uuid4(),
            recorrido_id=recorrido.id,
            sucursal_id=datos.sucursal_id,
            estado=EN_CURSO,
            iniciado_por_id=usuario.id,
            created_at=datetime.now(UTC),
        )
        await self.repo.agregar(control)
        await self.repo.confirmar()
        return ControlDescargaResponse(
            message="Control iniciado. Escaneá cada paquete a medida que baja.",
            data=await self._dato(await self.repo.obtener_control(control.id)),
        )

    async def detalle(self, id: uuid.UUID) -> ControlDescargaResponse:
        return ControlDescargaResponse(data=await self._dato(await self._control(id)))

    async def _control(self, id: uuid.UUID) -> Any:
        control = await self.repo.obtener_control(id)
        if control is None:
            raise NotFoundException("No existe ese control de descarga.")
        return control

    async def registrar_lectura(self, id: uuid.UUID, datos: RegistrarLecturaRequest, usuario: Any) -> ResultadoLecturaResponse:
        control = await self._control(id)
        if control.estado != EN_CURSO:
            raise ValidationException(
                message="El control ya está cerrado.",
                errors=[{"field": "codigo", "message": "Para revisar un paquete usá la trazabilidad del monitor."}],
            )
        codigo = normalizar_codigo(datos.codigo)
        if not es_codigo_de_paquete(codigo):
            raise ValidationException(
                message="Ese código no es de un paquete.",
                errors=[{"field": "codigo", "message": "Escaneá la etiqueta del paquete (PAQ-XXXXXXXXXX)."}],
            )

        anterior = next((lectura for lectura in control.lecturas if lectura.codigo == codigo), None)
        if anterior is not None:
            return self._resultado(codigo, anterior.resultado, "Ya estaba leído. No se contó dos veces.", await self._dato(control), repetida=True)

        esperados = {p.numero_paquete: p for p in await self._paradas_en(control.recorrido_id, control.sucursal_id)}
        ahora = datetime.now(UTC)
        if codigo in esperados:
            await self._recibir(control, esperados[codigo].paquete_id, usuario, ahora)
            resultado, mensaje, paquete_id = CORRECTO, "Correcto: tenía que llegar a esta sucursal.", esperados[codigo].paquete_id
        else:
            paquete = await self.repo.paquete_por_numero(codigo)
            if paquete is None:
                resultado, mensaje, paquete_id = DESCONOCIDO, "No existe un paquete con ese número.", None
            else:
                recorrido = await self.repo.obtener_recorrido(control.recorrido_id)
                del_recorrido = any(rp.paquete_id == paquete.id for rp in recorrido.paquetes)
                destino = paquete.envio.sucursal_destino.nombre if paquete.envio.sucursal_destino else None
                resultado, paquete_id = SOBRANTE, paquete.id
                mensaje = motivo_sobrante(
                    es_del_recorrido=del_recorrido,
                    sucursal_destino_del_paquete=destino if destino != control.sucursal.nombre else None,
                    sucursal_control=control.sucursal.nombre,
                )
        await self.repo.agregar(LecturaDescargaModel(
            control_id=control.id, paquete_id=paquete_id, codigo=codigo, resultado=resultado,
            detalle=mensaje[:255], usuario_id=usuario.id, created_at=ahora,
        ))
        await self.repo.confirmar()
        return self._resultado(codigo, resultado, mensaje, await self._dato(await self.repo.obtener_control(control.id)))

    async def _recibir(self, control: Any, paquete_id: uuid.UUID, usuario: Any, ahora: datetime) -> None:
        """El paquete bajó en su sucursal: si todavía figuraba en tránsito, se registra la llegada."""
        recorrido = await self.repo.obtener_recorrido(control.recorrido_id)
        asignacion = next(rp for rp in recorrido.paquetes if rp.paquete_id == paquete_id)
        paquete = asignacion.paquete
        if paquete.estado == EstadoPaqueteEnum.EN_TRANSITO.value:
            paquete.estado = EstadoPaqueteEnum.EN_SUCURSAL_DESTINO.value
            paquete.sucursal_actual_id = control.sucursal_id
            await self.repo.agregar(HistorialEstadoPaqueteModel(
                paquete_id=paquete.id,
                estado_anterior=EstadoPaqueteEnum.EN_TRANSITO.value,
                estado_nuevo=EstadoPaqueteEnum.EN_SUCURSAL_DESTINO.value,
                usuario_id=usuario.id,
                sucursal_id=control.sucursal_id,
                observacion=f"Recibido en el control de descarga de {control.sucursal.nombre}.",
                created_at=ahora,
            ))
        if asignacion.estado_en_recorrido == EstadoRecorridoPaqueteEnum.PENDIENTE.value:
            asignacion.estado_en_recorrido = EstadoRecorridoPaqueteEnum.ENTREGADO.value
        if recorrido.paquetes and all(
            rp.estado_en_recorrido != EstadoRecorridoPaqueteEnum.PENDIENTE.value for rp in recorrido.paquetes
        ):
            recorrido.estado = EstadoRecorridoEnum.FINALIZADO.value

    async def cerrar(self, id: uuid.UUID, datos: CerrarControlRequest, usuario: Any) -> ControlDescargaResponse:
        control = await self._control(id)
        if control.estado == CERRADO:
            return ControlDescargaResponse(message="El control ya estaba cerrado.", data=await self._dato(control))
        dato = await self._dato(control)
        for faltante in (p for p in dato.esperados if not p.verificado):
            motivo = MotivoAlertaRecorridoEnum.FALTANTE_EN_DESCARGA.value
            if not await self.repo.tiene_alerta_abierta(faltante.paquete_id, motivo):
                await self.repo.agregar(AlertaRecorridoModel(
                    id=uuid.uuid4(), paquete_id=faltante.paquete_id, recorrido_id=control.recorrido_id,
                    motivo=motivo, resuelta=False,
                ))
        control.estado = CERRADO
        control.cerrado_por_id = usuario.id
        control.cerrado_at = datetime.now(UTC)
        control.observaciones = (datos.observaciones or "").strip() or None
        await self.repo.confirmar()
        dato = await self._dato(await self.repo.obtener_control(control.id))
        mensaje = (
            "Control cerrado. Todo lo esperado llegó."
            if not dato.faltantes
            else f"Control cerrado. {dato.faltantes} {'paquete quedó' if dato.faltantes == 1 else 'paquetes quedaron'} como faltante en el monitor."
        )
        return ControlDescargaResponse(message=mensaje, data=dato)

    # --- Armado de respuestas -----------------------------------------------

    @staticmethod
    def _resultado(codigo: str, resultado: str, mensaje: str, control: ControlDescargaData, *, repetida: bool = False):
        return ResultadoLecturaResponse(data=ResultadoLecturaData(
            codigo=codigo, resultado=resultado, repetida=repetida, mensaje=mensaje, control=control,
        ))

    async def _dato(self, control: Any) -> ControlDescargaData:
        esperados = await self._paradas_en(control.recorrido_id, control.sucursal_id)
        correctas = {lectura.paquete_id: lectura for lectura in control.lecturas if lectura.resultado == CORRECTO}
        recorrido_completo = await self.repo.obtener_recorrido(control.recorrido_id)
        entrega = {rp.paquete_id: rp.paquete.envio.tipo_entrega for rp in recorrido_completo.paquetes}
        paquetes = [
            PaqueteEsperadoData(
                paquete_id=p.paquete_id,
                numero_paquete=p.numero_paquete,
                descripcion=p.descripcion,
                destinatario_nombre=p.destinatario_nombre,
                tipo_entrega=entrega.get(p.paquete_id, "sucursal"),
                estado=p.estado,
                estado_etiqueta=etiqueta_estado(p.estado),
                verificado=p.paquete_id in correctas,
                verificado_at=correctas[p.paquete_id].created_at if p.paquete_id in correctas else None,
                verificado_por=_nombre(correctas[p.paquete_id].usuario) if p.paquete_id in correctas else None,
            )
            for p in esperados
        ]
        sobrantes = [
            LecturaDescargaData(
                codigo=lectura.codigo, resultado=lectura.resultado, detalle=lectura.detalle,
                usuario_nombre=_nombre(lectura.usuario), created_at=lectura.created_at,
            )
            for lectura in control.lecturas
            if lectura.resultado != CORRECTO
        ]
        verificados = sum(1 for p in paquetes if p.verificado)
        recorrido = control.recorrido
        return ControlDescargaData(
            id=control.id,
            estado=control.estado,
            recorrido=RecorridoDescargaData(
                id=recorrido.id, fecha=recorrido.fecha, estado=recorrido.estado,
                repartidor_nombre=_nombre(recorrido.repartidor.usuario) or "Repartidor",
                sucursal_origen=recorrido.sucursal_origen.nombre,
            ),
            sucursal=SucursalDescargaData(id=control.sucursal.id, nombre=control.sucursal.nombre),
            esperados=sorted(paquetes, key=lambda p: (p.verificado, p.numero_paquete)),
            sobrantes=sobrantes,
            total_esperados=len(paquetes),
            verificados=verificados,
            faltantes=len(paquetes) - verificados,
            resumen=resumen_control(len(paquetes), verificados, len(sobrantes)),
            iniciado_por=_nombre(control.iniciado_por),
            created_at=control.created_at,
            cerrado_por=_nombre(control.cerrado_por),
            cerrado_at=control.cerrado_at,
            observaciones=control.observaciones,
        )
