"""Ejecución de recorridos y constancias; reutiliza la planificación de HU10."""

import hashlib
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from app.application.interfaces.repositorio_entregas import IRepositorioEntregas
from app.application.interfaces.repositorio_recorridos import IRepositorioRecorridos
from app.application.interfaces.servicio_recorridos import IServicioRecorridos
from app.application.interfaces.servicio_reparto import IServicioReparto
from app.contracts.recorridos import RecorridoResponse
from app.contracts.reparto import (
    ContactoEntregaData,
    ContactoEntregaResponse,
    EventoEntregaData,
    EventoEntregaResponse,
    RegistrarEntregaRequest,
    RegistrarLlegadaRequest,
    RegistrarVisitaFallidaRequest,
    UbicacionData,
    UbicacionRequest,
    UbicacionResponse,
)
from app.core.config import settings
from app.core.exceptions import (
    DuplicateEntryException,
    ForbiddenAccessException,
    NotFoundException,
    ValidationException,
)
from app.domain.constants.estados_logistica import (
    CanalNotificacionEnum,
    DestinatarioNotificacionEnum,
    EstadoNotificacionEnum,
    EstadoPaqueteEnum,
    EstadoRecorridoEnum,
    EstadoRecorridoPaqueteEnum,
    ResultadoEventoEntregaEnum,
    TipoAvisoEnum,
    TipoDistanciaEnum,
    TipoEventoEntregaEnum,
)
from app.domain.rules.circuito_rules import agoto_visitas, estado_al_llegar, sumar_dias_habiles
from app.domain.rules.recepcion_rules import normalizar_codigo_escaneado
from app.domain.rules.reparto_rules import decodificar_firma_png, receptor_mayor_de_16
from app.domain.rules.telefono_rules import normalizar_telefono_whatsapp
from app.infrastructure.db.models import (
    EventoEntregaModel,
    HistorialEstadoPaqueteModel,
    NotificacionEnvioModel,
    PosicionActualRepartidorModel,
)


def _destino_whatsapp(telefono: str | None) -> str:
    """Se audita el número al que realmente se envía; si no es válido, el original para poder corregirlo."""
    numero = normalizar_telefono_whatsapp(telefono, settings.WHATSAPP_CODIGO_PAIS)
    return f"+{numero}" if numero else (telefono or "")


class ServicioReparto(IServicioReparto):
    def __init__(
        self,
        repo_recorridos: IRepositorioRecorridos,
        repo_entregas: IRepositorioEntregas,
        servicio_recorridos: IServicioRecorridos,
    ):
        self.repo = repo_recorridos
        self.entregas = repo_entregas
        self.recorridos = servicio_recorridos

    async def _perfil(self, usuario: Any):
        perfil = await self.repo.obtener_repartidor(usuario.id)
        if not perfil or not perfil.activo:
            raise ForbiddenAccessException("Se requiere un perfil de repartidor activo.")
        return perfil

    async def _autorizado(self, id: uuid.UUID, usuario: Any, *, bloquear: bool = False):
        perfil = await self._perfil(usuario)
        if bloquear:
            await self.repo.bloquear_recorrido(id, usuario.id)
        recorrido = await self.repo.obtener_recorrido(id)
        if not recorrido or recorrido.repartidor_id != usuario.id:
            raise NotFoundException("No se encontró un recorrido asignado con ese identificador.")
        if perfil.tipo_reparto != recorrido.tipo_distancia:
            raise ForbiddenAccessException("El tipo de recorrido no corresponde al perfil del repartidor.")
        return recorrido

    def _validar_activo(self, recorrido):
        if recorrido.estado != EstadoRecorridoEnum.EN_CURSO.value:
            raise ValidationException(message="El recorrido debe estar EN_CURSO para registrar esta operación.")

    async def listar(self, usuario: Any, fecha: date | None = None, estado: str | None = None):
        await self._perfil(usuario)
        return await self.recorridos.listar(repartidor_id=usuario.id, fecha=fecha, estado=estado)

    async def obtener(self, id: uuid.UUID, usuario: Any):
        await self._autorizado(id, usuario)
        return await self.recorridos.obtener(id)

    async def iniciar(self, id: uuid.UUID, usuario: Any):
        await self._autorizado(id, usuario, bloquear=True)
        return await self.recorridos.iniciar(id, usuario)

    async def optimizar(self, id: uuid.UUID, usuario: Any, desde: tuple[float, float] | None):
        recorrido = await self._autorizado(id, usuario, bloquear=True)
        if recorrido.estado == EstadoRecorridoEnum.FINALIZADO.value:
            raise ValidationException(message="El recorrido ya terminó: no hay nada que reordenar.")
        return await self.recorridos.optimizar(id, desde)

    async def obtener_ubicacion(self, id: uuid.UUID, usuario: Any):
        recorrido = await self._autorizado(id, usuario)
        posicion = await self.repo.obtener_posicion(usuario.id)
        return UbicacionResponse(
            data=self._posicion_data(posicion) if posicion and posicion.recorrido_id == recorrido.id else None
        )

    def _posicion_data(self, posicion):
        return UbicacionData(
            latitud=posicion.latitud, longitud=posicion.longitud, actualizado_at=posicion.actualizado_at
        )

    async def actualizar_ubicacion(self, id: uuid.UUID, datos: UbicacionRequest, usuario: Any):
        recorrido = await self._autorizado(id, usuario, bloquear=True)
        self._validar_activo(recorrido)
        ahora = datetime.now(UTC)
        posicion = await self.repo.obtener_posicion(usuario.id)
        if posicion is None:
            posicion = PosicionActualRepartidorModel(repartidor_id=usuario.id)
            await self.repo.agregar(posicion)
        posicion.recorrido_id = id
        posicion.latitud, posicion.longitud = datos.latitud, datos.longitud
        posicion.actualizado_at = ahora

        await self.repo.confirmar()
        return UbicacionResponse(data=self._posicion_data(posicion))

    async def registrar_llegada(
        self, id: uuid.UUID, datos: RegistrarLlegadaRequest, usuario: Any
    ) -> tuple[RecorridoResponse, list[uuid.UUID]]:
        """Llegada a una sucursal de un recorrido entre sucursales, marcada por el repartidor.

        Los paquetes que bajan ahí quedan listos para retirar (si es su sucursal de
        retiro), en espera del reparto a domicilio o, si vuelven al remitente, en
        camino a su origen. Devuelve el recorrido actualizado y los paquetes que
        quedaron listos para retirar, para avisar al cliente.
        """
        recorrido = await self._autorizado(id, usuario, bloquear=True)
        self._validar_activo(recorrido)
        if recorrido.tipo_distancia != TipoDistanciaEnum.LARGA.value:
            raise ValidationException(message="La llegada a una sucursal se marca solo en recorridos entre sucursales.")
        await self.repo.sincronizar()
        paradas = [
            (sucursal, [rp for rp in grupo if rp.estado_en_recorrido == EstadoRecorridoPaqueteEnum.PENDIENTE.value])
            for sucursal, grupo in await self.recorridos.paradas_en_sucursales(recorrido)
        ]
        pendientes = [(sucursal, grupo) for sucursal, grupo in paradas if grupo]
        if not pendientes:
            raise ValidationException(message="No quedan sucursales pendientes en este recorrido.")
        proxima, grupo = pendientes[0]
        if proxima.id != datos.sucursal_id:
            raise ValidationException(
                message=f"Primero marcá la llegada a {proxima.nombre}: las sucursales se visitan en orden.",
                errors=[{"field": "sucursal_id", "message": f"La próxima parada es {proxima.nombre}."}],
            )

        ahora = datetime.now(UTC)
        llegables = (
            EstadoPaqueteEnum.EN_TRANSITO.value,
            EstadoPaqueteEnum.EN_SUCURSAL_DESTINO.value,
            EstadoPaqueteEnum.EN_DEVOLUCION.value,
        )
        listos: list[uuid.UUID] = []
        for rp in grupo:
            paquete = rp.paquete
            envio = paquete.envio
            destino = estado_al_llegar(
                tipo_entrega=envio.tipo_entrega,
                sucursal_destino_id=envio.sucursal_destino_id,
                sucursal_origen_id=paquete.sucursal_origen_id,
                en_devolucion=paquete.en_devolucion,
                sucursal_llegada_id=proxima.id,
            )
            if paquete.estado in llegables and paquete.estado != destino:
                anterior = paquete.estado
                paquete.estado = destino
                paquete.sucursal_actual_id = proxima.id
                observacion = f"Llegó a {proxima.nombre} en el recorrido entre sucursales."
                if destino == EstadoPaqueteEnum.LISTO_PARA_RETIRO.value:
                    paquete.retiro_hasta = None if paquete.en_devolucion else sumar_dias_habiles(
                        ahora, settings.PLAZO_RETIRO_DIAS_HABILES
                    )
                    observacion += (
                        " Vuelve al remitente: lo retira quien lo envió." if paquete.en_devolucion
                        else " Queda listo para retirar."
                    )
                    listos.append(paquete.id)
                await self.repo.agregar(HistorialEstadoPaqueteModel(
                    paquete_id=paquete.id,
                    estado_anterior=anterior,
                    estado_nuevo=destino,
                    usuario_id=usuario.id,
                    sucursal_id=proxima.id,
                    latitud=datos.latitud,
                    longitud=datos.longitud,
                    observacion=observacion,
                    created_at=ahora,
                ))
            rp.estado_en_recorrido = EstadoRecorridoPaqueteEnum.ENTREGADO.value
        self._finalizar_si_completo(recorrido)
        await self.repo.confirmar()

        respuesta = await self.recorridos.obtener(id)
        cantidad = len(grupo)
        respuesta.message = (
            f"Llegada a {proxima.nombre} registrada: "
            f"{cantidad} {'paquete bajó' if cantidad == 1 else 'paquetes bajaron'} en esta sucursal."
        )
        return respuesta, listos

    def _paquete(self, recorrido, codigo: str):
        codigo = normalizar_codigo_escaneado(codigo)
        for rp in recorrido.paquetes:
            if codigo in (rp.paquete.numero_paquete, str(rp.paquete_id).upper()):
                return rp
        raise NotFoundException("El paquete no pertenece al recorrido asignado.")

    def _validar_domicilio(self, recorrido, rp):
        if recorrido.tipo_distancia != TipoDistanciaEnum.CORTA.value or rp.paquete.envio.tipo_entrega != "domicilio":
            raise ValidationException(message="Esta operación requiere una entrega a domicilio de corta distancia.")

    async def contacto(self, id: uuid.UUID, codigo: str, usuario: Any):
        recorrido = await self._autorizado(id, usuario)
        self._validar_activo(recorrido)
        rp = self._paquete(recorrido, codigo)
        self._validar_domicilio(recorrido, rp)
        telefono = (rp.paquete.envio.destinatario_telefono or "").strip() or None
        return ContactoEntregaResponse(
            data=ContactoEntregaData(
                paquete_id=rp.paquete_id,
                destinatario_nombre=rp.paquete.envio.destinatario_nombre,
                telefono=telefono,
                telefono_disponible=telefono is not None,
            )
        )

    async def registrar_entrega(self, id: uuid.UUID, codigo: str, datos: RegistrarEntregaRequest, usuario: Any):
        return await self._registrar(id, codigo, datos, usuario, exitoso=True)

    async def registrar_visita_fallida(
        self, id: uuid.UUID, codigo: str, datos: RegistrarVisitaFallidaRequest, usuario: Any
    ):
        return await self._registrar(id, codigo, datos, usuario, exitoso=False)

    async def _registrar(self, id, codigo, datos, usuario, *, exitoso):
        recorrido = await self._autorizado(id, usuario, bloquear=True)
        rp = self._paquete(recorrido, codigo)
        self._validar_domicilio(recorrido, rp)
        huella = hashlib.sha256(datos.model_dump_json().encode()).hexdigest()
        anterior = await self.entregas.obtener_por_operacion(datos.operacion_id)
        if anterior:
            if (
                anterior.recorrido_id != id
                or anterior.paquete_id != rp.paquete_id
                or anterior.usuario_registro_id != usuario.id
                or anterior.solicitud_hash != huella
            ):
                raise DuplicateEntryException(message="El operacion_id ya fue utilizado con otros datos.")
            # Liberar el lock antes de que el aviso se procese con otra sesión.
            await self.repo.confirmar()
            return self._evento_response(anterior)
        if rp.estado_en_recorrido != EstadoRecorridoPaqueteEnum.PENDIENTE.value:
            raise DuplicateEntryException(message="El paquete ya fue procesado en este recorrido.")
        self._validar_activo(recorrido)
        if rp.paquete.estado != EstadoPaqueteEnum.EN_REPARTO.value:
            raise DuplicateEntryException(message="El paquete ya fue procesado o no está EN_REPARTO.")

        ahora = datetime.now(UTC)
        if exitoso and not receptor_mayor_de_16(datos.receptor_fecha_nacimiento, ahora.date()):
            raise ValidationException(
                message="El receptor debe ser mayor de 16 años y tener una fecha de nacimiento válida.",
                errors=[{"field": "receptor_fecha_nacimiento", "message": "Edad no permitida."}],
            )
        paquete = rp.paquete
        nuevo_estado = EstadoPaqueteEnum.ENTREGADO.value if exitoso else EstadoPaqueteEnum.ENTREGA_FALLIDA.value
        # Tras la última visita sin éxito el paquete deja de salir a reparto: al volver
        # el vehículo queda en la sucursal para que el destinatario lo retire.
        visitas = 0 if exitoso else await self.entregas.contar_visitas_fallidas(paquete.id) + 1
        queda_para_retiro = not exitoso and agoto_visitas(visitas, settings.MAX_VISITAS_DOMICILIO)
        evento = EventoEntregaModel(
            id=uuid.uuid4(),
            operacion_id=datos.operacion_id,
            solicitud_hash=huella,
            recorrido_id=id,
            paquete_id=paquete.id,
            tipo_evento=TipoEventoEntregaEnum.ENTREGA_DOMICILIO.value,
            resultado=ResultadoEventoEntregaEnum.EXITOSO.value if exitoso else ResultadoEventoEntregaEnum.FALLIDO.value,
            usuario_registro_id=usuario.id,
            created_at=ahora,
        )
        if exitoso:
            evento.receptor_nombre = datos.receptor_nombre
            evento.receptor_documento = datos.receptor_documento
            evento.receptor_fecha_nacimiento = datos.receptor_fecha_nacimiento
            evento.es_autorizado = datos.es_autorizado
            evento.firma_imagen = decodificar_firma_png(datos.firma_base64)
            evento.firma_content_type = "image/png"
        else:
            evento.es_autorizado = False
            evento.motivo_fallo = datos.motivo_fallo
        posicion = await self.repo.obtener_posicion(usuario.id)
        if posicion and posicion.recorrido_id == id:
            evento.latitud, evento.longitud = posicion.latitud, posicion.longitud
        # Una visita fallida vuelve con el vehículo a la sucursal de donde salió: desde ahí
        # se reintenta en otro recorrido o, tras la última visita, se retira.
        await self.repo.actualizar_estado_paquete(
            paquete.id,
            EstadoPaqueteEnum.EN_REPARTO.value,
            nuevo_estado,
            None if exitoso else recorrido.sucursal_origen_id,
        )
        if queda_para_retiro:
            await self.repo.actualizar_estado_paquete(
                paquete.id, nuevo_estado, EstadoPaqueteEnum.LISTO_PARA_RETIRO.value, recorrido.sucursal_origen_id
            )
            paquete.retiro_hasta = sumar_dias_habiles(ahora, settings.PLAZO_RETIRO_DIAS_HABILES)
        rp.estado_en_recorrido = (
            EstadoRecorridoPaqueteEnum.ENTREGADO.value if exitoso else EstadoRecorridoPaqueteEnum.FALLIDO.value
        )
        await self.repo.agregar(evento)
        await self.repo.agregar(
            HistorialEstadoPaqueteModel(
                paquete_id=paquete.id,
                estado_anterior=EstadoPaqueteEnum.EN_REPARTO.value,
                estado_nuevo=nuevo_estado,
                usuario_id=usuario.id,
                latitud=evento.latitud,
                longitud=evento.longitud,
                created_at=ahora,
                # El historial público no incluye identidad, documento, firma ni el motivo libre.
                observacion="Entrega a domicilio completada." if exitoso else "Aviso de visita: entrega no concretada.",
            )
        )
        if queda_para_retiro:
            await self.repo.agregar(
                HistorialEstadoPaqueteModel(
                    paquete_id=paquete.id,
                    estado_anterior=nuevo_estado,
                    estado_nuevo=EstadoPaqueteEnum.LISTO_PARA_RETIRO.value,
                    usuario_id=None,
                    sucursal_id=recorrido.sucursal_origen_id,
                    created_at=ahora + timedelta(seconds=1),
                    observacion=(
                        f"Se hicieron las {settings.MAX_VISITAS_DOMICILIO} visitas previstas: queda para retirar "
                        "en la sucursal al volver el vehículo."
                    ),
                )
            )
        if not exitoso:
            # El aviso pendiente se guarda en la MISMA transacción que la visita.
            # Un aviso por canal (email y WhatsApp), como pide HU12 Escenario 3.
            await self.repo.sincronizar()
            for canal, destino in (
                (CanalNotificacionEnum.EMAIL.value, paquete.envio.destinatario_email),
                (CanalNotificacionEnum.WHATSAPP.value, _destino_whatsapp(paquete.envio.destinatario_telefono)),
            ):
                await self.repo.agregar(
                    NotificacionEnvioModel(
                        id=uuid.uuid4(),
                        envio_id=paquete.envio_id,
                        evento_entrega_id=evento.id,
                        paquete_id=paquete.id,
                        tipo_aviso=TipoAvisoEnum.VISITA_FALLIDA.value,
                        canal=canal,
                        destinatario_tipo=DestinatarioNotificacionEnum.DESTINATARIO.value,
                        destino=(destino or "").strip()[:150],
                        estado=EstadoNotificacionEnum.PENDIENTE.value,
                    )
                )
        self._finalizar_si_completo(recorrido)
        await self.repo.confirmar()
        return self._evento_response(evento)

    def _finalizar_si_completo(self, recorrido):
        if recorrido.paquetes and all(
            rp.estado_en_recorrido != EstadoRecorridoPaqueteEnum.PENDIENTE.value for rp in recorrido.paquetes
        ):
            recorrido.estado = EstadoRecorridoEnum.FINALIZADO.value

    def _evento_response(self, evento):
        return EventoEntregaResponse(
            data=EventoEntregaData(
                evento_id=evento.id,
                paquete_id=evento.paquete_id,
                recorrido_id=evento.recorrido_id,
                resultado=evento.resultado,
                receptor_nombre=evento.receptor_nombre,
                receptor_documento=evento.receptor_documento,
                es_autorizado=evento.es_autorizado,
                firma_disponible=bool(evento.firma_imagen),
                motivo_fallo=evento.motivo_fallo,
                fecha_hora=evento.created_at,
            )
        )

    async def obtener_firma(self, id: uuid.UUID, evento_id: uuid.UUID, usuario: Any):
        await self._autorizado(id, usuario)
        evento = await self.entregas.obtener_evento(evento_id)
        if (
            not evento
            or evento.recorrido_id != id
            or evento.usuario_registro_id != usuario.id
            or not evento.firma_imagen
        ):
            raise NotFoundException("No se encontró una firma para ese evento del recorrido.")
        return evento.firma_imagen
