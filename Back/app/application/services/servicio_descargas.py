"""Control de carga y descarga de los recorridos (escaneo en cada traspaso).

- **Carga** (sucursal de origen, antes de salir): se escanea cada paquete que sube
  al vehículo. Al cerrar, lo que no se cargó sale del recorrido y queda como
  alerta, así el recorrido viaja solo con lo que realmente lleva.
- **Descarga** (sucursal de destino, al llegar un recorrido de larga distancia):
  se escanea cada paquete que baja. Lo que se retira en esa sucursal queda listo
  para retirar, con su plazo; al cerrar, lo que no apareció queda como faltante.
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
from app.core.config import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.domain.constants.estados_logistica import (
    EstadoPaqueteEnum,
    EstadoRecorridoEnum,
    EstadoRecorridoPaqueteEnum,
    MotivoAlertaRecorridoEnum,
    TipoControlEnum,
    TipoDistanciaEnum,
)
from app.domain.rules.circuito_rules import estado_al_llegar, sumar_dias_habiles
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
from app.domain.rules.recorrido_rules import ESTADOS_RECORRIDO_EDITABLES
from app.infrastructure.db.models import (
    AlertaRecorridoModel,
    ControlDescargaModel,
    HistorialEstadoPaqueteModel,
    LecturaDescargaModel,
)

CARGA = TipoControlEnum.CARGA.value
DESCARGA = TipoControlEnum.DESCARGA.value


def _nombre(usuario: Any) -> str | None:
    return getattr(usuario, "nombre", None) if usuario else None


class ServicioDescargas:
    def __init__(self, repositorio: IRepositorioDescargas, servicio_recorridos: IServicioRecorridos):
        self.repo = repositorio
        self.recorridos = servicio_recorridos

    # --- Qué se espera en cada control ---------------------------------------

    async def _esperados(self, tipo: str, recorrido_id: uuid.UUID, sucursal_id: int) -> list[dict[str, Any]]:
        """Paquetes que tienen que subir (carga) o bajar en la sucursal (descarga)."""
        recorrido = await self.repo.obtener_recorrido(recorrido_id)
        if recorrido is None:
            return []
        return (await self._esperados_por_recorrido(tipo, [recorrido], sucursal_id))[recorrido.id]

    async def _esperados_por_recorrido(
        self, tipo: str, recorridos: list[Any], sucursal_id: int
    ) -> dict[uuid.UUID, list[dict[str, Any]]]:
        """Lo mismo para varios recorridos ya cargados, sin consultas por recorrido.

        En la carga sube todo el recorrido; en la descarga, lo que tiene parada en
        esta sucursal según la misma regla que el detalle del recorrido.
        """
        if tipo == CARGA:
            por_recorrido = {r.id: sorted(r.paquetes, key=lambda rp: rp.orden) for r in recorridos}
        else:
            por_recorrido = await self.recorridos.paquetes_que_bajan_en(recorridos, sucursal_id)
        return {
            recorrido_id: [
                {
                    "paquete_id": rp.paquete_id,
                    "numero_paquete": rp.paquete.numero_paquete,
                    "descripcion": rp.paquete.descripcion,
                    "destinatario_nombre": rp.paquete.envio.destinatario_nombre,
                    "estado": rp.paquete.estado,
                    "tipo_entrega": rp.paquete.envio.tipo_entrega,
                }
                for rp in paquetes
            ]
            for recorrido_id, paquetes in por_recorrido.items()
        }

    # --- Recorridos para controlar en una sucursal ---------------------------

    async def recorridos_entrantes(self, sucursal_id: int, hoy: datetime | None = None) -> RecorridosEntrantesResponse:
        return await self._recorridos(sucursal_id, DESCARGA, hoy)

    async def recorridos_salientes(self, sucursal_id: int, hoy: datetime | None = None) -> RecorridosEntrantesResponse:
        return await self._recorridos(sucursal_id, CARGA, hoy)

    async def _recorridos(self, sucursal_id: int, tipo: str, hoy: datetime | None) -> RecorridosEntrantesResponse:
        if await self.repo.obtener_sucursal(sucursal_id) is None:
            raise NotFoundException("No existe esa sucursal.")
        hoy = hoy or datetime.now(UTC)
        desde = (hoy - timedelta(days=DIAS_RECORRIDOS_ENTRANTES)).date()
        if tipo == CARGA:
            recorridos = await self.repo.recorridos_desde(
                desde, tuple(ESTADOS_RECORRIDO_EDITABLES), sucursal_origen_id=sucursal_id
            )
        else:
            recorridos = await self.repo.recorridos_desde(
                desde, ESTADOS_RECORRIDO_CONTROLABLES,
                excluir_origen_id=sucursal_id, tipo_distancia=TipoDistanciaEnum.LARGA.value,
            )
        controles = await self.repo.controles_de_sucursal(sucursal_id, [r.id for r in recorridos], tipo)
        esperados_por_recorrido = await self._esperados_por_recorrido(tipo, recorridos, sucursal_id)
        resultado = []
        for recorrido in recorridos:
            esperados = esperados_por_recorrido[recorrido.id]
            if not esperados:
                continue
            control = controles.get(recorrido.id)
            ids = {p["paquete_id"] for p in esperados}
            verificados = (
                sum(1 for lectura in control.lecturas if lectura.resultado == CORRECTO and lectura.paquete_id in ids)
                if control
                else 0
            )
            resultado.append(RecorridoEntranteData(
                recorrido_id=recorrido.id,
                fecha=recorrido.fecha,
                estado=recorrido.estado,
                tipo_distancia=recorrido.tipo_distancia,
                repartidor_nombre=_nombre(recorrido.repartidor.usuario) or "Repartidor",
                sucursal_origen=recorrido.sucursal_origen.nombre,
                esperados=len(esperados),
                verificados=verificados,
                control_id=control.id if control else None,
                control_estado=control.estado if control else None,
            ))
        return RecorridosEntrantesResponse(data=resultado)

    # --- Control ------------------------------------------------------------

    async def iniciar(self, datos: IniciarControlRequest, usuario: Any) -> ControlDescargaResponse:
        tipo = datos.tipo
        existente = await self.repo.obtener_control_por(datos.recorrido_id, datos.sucursal_id, tipo)
        if existente:
            return ControlDescargaResponse(data=await self._dato(existente))
        recorrido = await self.repo.obtener_recorrido(datos.recorrido_id)
        if recorrido is None:
            raise NotFoundException("No existe ese recorrido.")
        if await self.repo.obtener_sucursal(datos.sucursal_id) is None:
            raise NotFoundException("No existe esa sucursal.")
        if tipo == CARGA:
            self._validar_carga(recorrido, datos.sucursal_id)
        else:
            self._validar_descarga(recorrido)
        if not await self._esperados(tipo, recorrido.id, datos.sucursal_id):
            raise ValidationException(
                message="Este recorrido no deja paquetes en esa sucursal.",
                errors=[{"field": "sucursal_id", "message": "Elegí la sucursal donde descarga el recorrido."}],
            )
        control = ControlDescargaModel(
            id=uuid.uuid4(),
            recorrido_id=recorrido.id,
            sucursal_id=datos.sucursal_id,
            tipo=tipo,
            estado=EN_CURSO,
            iniciado_por_id=usuario.id,
            created_at=datetime.now(UTC),
        )
        await self.repo.agregar(control)
        await self.repo.confirmar()
        mensaje = (
            "Control de carga iniciado. Escaneá cada paquete a medida que sube al vehículo."
            if tipo == CARGA
            else "Control iniciado. Escaneá cada paquete a medida que baja."
        )
        return ControlDescargaResponse(message=mensaje, data=await self._dato(await self.repo.obtener_control(control.id)))

    @staticmethod
    def _validar_carga(recorrido: Any, sucursal_id: int) -> None:
        if recorrido.sucursal_origen_id != sucursal_id:
            raise ValidationException(
                message="La carga se controla en la sucursal de donde sale el recorrido.",
                errors=[{"field": "sucursal_id", "message": "Elegí la sucursal de origen del recorrido."}],
            )
        if recorrido.estado not in ESTADOS_RECORRIDO_EDITABLES:
            raise ValidationException(
                message="El recorrido ya salió: la carga se controla antes de iniciarlo.",
                errors=[{"field": "recorrido_id", "message": f"Estado del recorrido: '{recorrido.estado}'."}],
            )

    @staticmethod
    def _validar_descarga(recorrido: Any) -> None:
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
            return self._resultado(codigo, anterior.resultado, "Ya estaba leído. No se contó dos veces.",
                                   await self._dato(control), repetida=True)

        esperados = {p["numero_paquete"]: p for p in await self._esperados(control.tipo, control.recorrido_id, control.sucursal_id)}
        ahora = datetime.now(UTC)
        listo = False
        if codigo in esperados:
            paquete_id = esperados[codigo]["paquete_id"]
            resultado = CORRECTO
            if control.tipo == CARGA:
                mensaje = "Correcto: va en este recorrido."
            else:
                listo = await self._recibir(control, paquete_id, usuario, ahora)
                mensaje = (
                    "Correcto: se retira en esta sucursal. Guardalo en el sector de retiros."
                    if listo
                    else "Correcto: tenía que llegar a esta sucursal."
                )
        else:
            paquete = await self.repo.paquete_por_numero(codigo)
            if paquete is None:
                resultado, mensaje, paquete_id = DESCONOCIDO, "No existe un paquete con ese número.", None
            else:
                recorrido = await self.repo.obtener_recorrido(control.recorrido_id)
                del_recorrido = any(rp.paquete_id == paquete.id for rp in recorrido.paquetes)
                destino = paquete.envio.sucursal_destino.nombre if paquete.envio.sucursal_destino else None
                resultado, paquete_id = SOBRANTE, paquete.id
                if control.tipo == CARGA:
                    mensaje = "No va en este recorrido. Dejalo en la sucursal."
                else:
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
        return self._resultado(
            codigo, resultado, mensaje, await self._dato(await self.repo.obtener_control(control.id)),
            paquete_id=paquete_id, listo_para_retiro=listo,
        )

    async def _recibir(self, control: Any, paquete_id: uuid.UUID, usuario: Any, ahora: datetime) -> bool:
        """El paquete bajó en la sucursal: se registra la llegada y, si se retira ahí,
        queda listo para retirar con su plazo. Devuelve si quedó listo para retirar."""
        recorrido = await self.repo.obtener_recorrido(control.recorrido_id)
        asignacion = next(rp for rp in recorrido.paquetes if rp.paquete_id == paquete_id)
        paquete = asignacion.paquete
        envio = paquete.envio
        destino = estado_al_llegar(
            tipo_entrega=envio.tipo_entrega,
            sucursal_destino_id=envio.sucursal_destino_id,
            sucursal_origen_id=paquete.sucursal_origen_id,
            en_devolucion=paquete.en_devolucion,
            sucursal_llegada_id=control.sucursal_id,
        )
        llegables = (EstadoPaqueteEnum.EN_TRANSITO.value, EstadoPaqueteEnum.EN_SUCURSAL_DESTINO.value)
        if paquete.estado in llegables and paquete.estado != destino:
            anterior = paquete.estado
            paquete.estado = destino
            paquete.sucursal_actual_id = control.sucursal_id
            observacion = f"Recibido en el control de descarga de {control.sucursal.nombre}."
            if destino == EstadoPaqueteEnum.LISTO_PARA_RETIRO.value:
                paquete.retiro_hasta = None if paquete.en_devolucion else sumar_dias_habiles(
                    ahora, settings.PLAZO_RETIRO_DIAS_HABILES
                )
                observacion += (
                    " Vuelve al remitente: lo retira quien lo envió." if paquete.en_devolucion
                    else " Queda listo para retirar."
                )
            await self.repo.agregar(HistorialEstadoPaqueteModel(
                paquete_id=paquete.id,
                estado_anterior=anterior,
                estado_nuevo=destino,
                usuario_id=usuario.id,
                sucursal_id=control.sucursal_id,
                observacion=observacion,
                created_at=ahora,
            ))
        if asignacion.estado_en_recorrido == EstadoRecorridoPaqueteEnum.PENDIENTE.value:
            asignacion.estado_en_recorrido = EstadoRecorridoPaqueteEnum.ENTREGADO.value
        if recorrido.paquetes and all(
            rp.estado_en_recorrido != EstadoRecorridoPaqueteEnum.PENDIENTE.value for rp in recorrido.paquetes
        ):
            recorrido.estado = EstadoRecorridoEnum.FINALIZADO.value
        return paquete.estado == EstadoPaqueteEnum.LISTO_PARA_RETIRO.value

    async def cerrar(self, id: uuid.UUID, datos: CerrarControlRequest, usuario: Any) -> ControlDescargaResponse:
        control = await self._control(id)
        if control.estado == CERRADO:
            return ControlDescargaResponse(message="El control ya estaba cerrado.", data=await self._dato(control))
        dato = await self._dato(control)
        faltantes = [p for p in dato.esperados if not p.verificado]
        quitados: list[str] = []
        if control.tipo == CARGA:
            quitados = await self._quitar_no_cargados(control, faltantes)
        else:
            for faltante in faltantes:
                await self._alertar(faltante.paquete_id, control.recorrido_id, MotivoAlertaRecorridoEnum.FALTANTE_EN_DESCARGA.value)
        control = await self._control(id)
        control.estado = CERRADO
        control.cerrado_por_id = usuario.id
        control.cerrado_at = datetime.now(UTC)
        control.observaciones = (datos.observaciones or "").strip() or None
        await self.repo.confirmar()
        dato = await self._dato(await self.repo.obtener_control(control.id))
        if not faltantes:
            mensaje = "Control cerrado. Todo lo esperado " + ("se cargó." if control.tipo == CARGA else "llegó.")
        elif control.tipo == CARGA:
            mensaje = (
                f"Control de carga cerrado. {len(quitados)} paquete(s) que no se cargaron salieron del recorrido "
                "y quedaron en la sucursal para el próximo."
                if quitados
                else "Control de carga cerrado. Los faltantes quedaron como alerta en el monitor."
            )
        else:
            mensaje = (
                f"Control cerrado. {len(faltantes)} "
                f"{'paquete quedó' if len(faltantes) == 1 else 'paquetes quedaron'} como faltante en el monitor."
            )
        return ControlDescargaResponse(message=mensaje, data=dato)

    async def _quitar_no_cargados(self, control: Any, faltantes: list[PaqueteEsperadoData]) -> list[str]:
        """Lo que no subió al vehículo sale del recorrido (si todavía se puede editar)."""
        quitados: list[str] = []
        recorrido = await self.repo.obtener_recorrido(control.recorrido_id)
        editable = recorrido is not None and recorrido.estado in ESTADOS_RECORRIDO_EDITABLES
        quedan = len(recorrido.paquetes) if recorrido else 0
        for faltante in faltantes:
            if editable and quedan > 1:
                await self.recorridos.quitar_paquete(control.recorrido_id, faltante.numero_paquete)
                quedan -= 1
                quitados.append(faltante.numero_paquete)
            await self._alertar(faltante.paquete_id, control.recorrido_id, MotivoAlertaRecorridoEnum.FALTANTE_EN_CARGA.value)
        return quitados

    async def _alertar(self, paquete_id: uuid.UUID, recorrido_id: uuid.UUID, motivo: str) -> None:
        if not await self.repo.tiene_alerta_abierta(paquete_id, motivo):
            await self.repo.agregar(AlertaRecorridoModel(
                id=uuid.uuid4(), paquete_id=paquete_id, recorrido_id=recorrido_id, motivo=motivo, resuelta=False,
            ))

    # --- Armado de respuestas -----------------------------------------------

    @staticmethod
    def _resultado(
        codigo: str,
        resultado: str,
        mensaje: str,
        control: ControlDescargaData,
        *,
        repetida: bool = False,
        paquete_id: uuid.UUID | None = None,
        listo_para_retiro: bool = False,
    ) -> ResultadoLecturaResponse:
        return ResultadoLecturaResponse(data=ResultadoLecturaData(
            codigo=codigo, resultado=resultado, repetida=repetida, mensaje=mensaje, control=control,
            paquete_id=paquete_id, listo_para_retiro=listo_para_retiro,
        ))

    async def _dato(self, control: Any) -> ControlDescargaData:
        esperados = await self._esperados(control.tipo, control.recorrido_id, control.sucursal_id)
        correctas = {lectura.paquete_id: lectura for lectura in control.lecturas if lectura.resultado == CORRECTO}
        paquetes = [
            PaqueteEsperadoData(
                paquete_id=p["paquete_id"],
                numero_paquete=p["numero_paquete"],
                descripcion=p["descripcion"],
                destinatario_nombre=p["destinatario_nombre"],
                tipo_entrega=p["tipo_entrega"],
                estado=p["estado"],
                estado_etiqueta=etiqueta_estado(p["estado"]),
                verificado=p["paquete_id"] in correctas,
                verificado_at=correctas[p["paquete_id"]].created_at if p["paquete_id"] in correctas else None,
                verificado_por=_nombre(correctas[p["paquete_id"]].usuario) if p["paquete_id"] in correctas else None,
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
            tipo=control.tipo,
            estado=control.estado,
            recorrido=RecorridoDescargaData(
                id=recorrido.id, fecha=recorrido.fecha, estado=recorrido.estado,
                tipo_distancia=recorrido.tipo_distancia,
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
