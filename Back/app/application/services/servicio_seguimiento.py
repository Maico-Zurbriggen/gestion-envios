from app.application.interfaces.repositorio_envios import IRepositorioEnvios
from app.contracts.reparto import UbicacionData
from app.contracts.seguimiento import (
    EventoSeguimientoData,
    PaqueteSeguimientoData,
    RetiroSeguimientoData,
    SeguimientoData,
    SeguimientoResponse,
)
from app.core.config import settings
from app.core.exceptions import NotFoundException
from app.domain.constants.estados_logistica import EstadoPaqueteEnum, EstadoRecorridoEnum, EstadoRecorridoPaqueteEnum
from app.domain.rules.circuito_rules import ESTADOS_ESPERANDO_RETIRO, sucursal_de_retiro
from app.domain.rules.codigos_rules import normalizar_token_seguimiento
from app.domain.rules.destino_rules import (
    formatear_destino_domicilio,
    formatear_destino_sucursal,
)

DESCRIPCIONES_PUBLICAS_ESTADO: dict[str, str] = {
    EstadoPaqueteEnum.EN_SUCURSAL_ORIGEN.value: "Paquete recibido en la terminal de origen.",
    EstadoPaqueteEnum.EN_TRANSITO.value: "En viaje hacia la sucursal de destino.",
    EstadoPaqueteEnum.EN_SUCURSAL_DESTINO.value: "Llegada a la sucursal de destino.",
    EstadoPaqueteEnum.LISTO_PARA_RETIRO.value: "Disponible para retirar en sucursal.",
    EstadoPaqueteEnum.EN_REPARTO.value: "En reparto hacia el domicilio.",
    EstadoPaqueteEnum.ENTREGADO.value: "Entrega a domicilio completada.",
    EstadoPaqueteEnum.ENTREGA_FALLIDA.value: "Aviso de visita: entrega no concretada.",
    EstadoPaqueteEnum.ENTREGADO_EN_SUCURSAL.value: "Retirado en sucursal.",
    EstadoPaqueteEnum.EN_DEVOLUCION.value: "No se retiró a tiempo: vuelve a quien lo envió.",
    EstadoPaqueteEnum.DEVUELTO.value: "Devuelto a quien lo envió.",
    EstadoPaqueteEnum.VENCIDO.value: "El registro venció porque el paquete no llegó a una sucursal a tiempo.",
}
"""Textos públicos del historial (HU04): nunca incluyen identidad, documentos ni observaciones internas."""


class ServicioSeguimiento:
    """Servicio de consulta pública de seguimiento de envíos por token (HU04)."""

    def __init__(self, repositorio_envios: IRepositorioEnvios):
        self.repo_envios = repositorio_envios

    async def obtener_seguimiento(self, token: str) -> SeguimientoResponse:
        envio = await self.repo_envios.obtener_por_token(normalizar_token_seguimiento(token))
        if not envio:
            raise NotFoundException("No se encontró un envío asociado a ese código de seguimiento.")

        if envio.tipo_entrega == "domicilio":
            destino = formatear_destino_domicilio(
                direccion=envio.direccion_destino,
                ciudad=envio.ciudad_destino,
                provincia=envio.provincia_destino,
            )
            latitud_destino = envio.latitud_destino
            longitud_destino = envio.longitud_destino
        else:
            sucursal = envio.sucursal_destino
            destino = formatear_destino_sucursal(
                nombre=sucursal.nombre,
                direccion=sucursal.direccion,
                ciudad=sucursal.ciudad,
                provincia=sucursal.provincia,
            )
            latitud_destino = sucursal.latitud
            longitud_destino = sucursal.longitud

        paquetes = [
            PaqueteSeguimientoData(
                numero_paquete=p.numero_paquete,
                estado=p.estado,
                descripcion=p.descripcion,
                observaciones=p.observaciones,
                fecha_registro=p.created_at,
                ultima_actualizacion=p.updated_at,
                historial=[EventoSeguimientoData(
                    estado_anterior=h.estado_anterior, estado=h.estado_nuevo, fecha_hora=h.created_at,
                    descripcion=DESCRIPCIONES_PUBLICAS_ESTADO.get(h.estado_nuevo, "Actualización del estado del paquete."),
                ) for h in sorted(p.historial_estados, key=lambda h: (h.created_at, h.id))],
                ubicacion_repartidor=self._ubicacion_publica(p),
                retiro=self._retiro(p, envio),
                visitas_fallidas=sum(
                    1 for h in p.historial_estados if h.estado_nuevo == EstadoPaqueteEnum.ENTREGA_FALLIDA.value
                ),
                max_visitas=settings.MAX_VISITAS_DOMICILIO,
                en_devolucion=p.en_devolucion,
            )
            for p in envio.paquetes
        ]

        return SeguimientoResponse(
            data=SeguimientoData(
                token_seguimiento=envio.token_seguimiento,
                tipo_entrega=envio.tipo_entrega,
                destino=destino,
                latitud_destino=latitud_destino,
                longitud_destino=longitud_destino,
                paquetes=paquetes,
            )
        )

    @staticmethod
    def _retiro(paquete, envio) -> RetiroSeguimientoData | None:
        """Solo cuando el paquete ya espera en la sucursal donde se retira."""
        if paquete.estado not in ESTADOS_ESPERANDO_RETIRO:
            return None
        sucursal_id = sucursal_de_retiro(
            tipo_entrega=envio.tipo_entrega,
            sucursal_destino_id=envio.sucursal_destino_id,
            sucursal_actual_id=paquete.sucursal_actual_id,
            sucursal_origen_id=paquete.sucursal_origen_id,
            estado=paquete.estado,
            en_devolucion=paquete.en_devolucion,
        )
        sucursal = paquete.sucursal_actual
        if sucursal is None or sucursal_id != sucursal.id:
            return None
        return RetiroSeguimientoData(
            sucursal=sucursal.nombre,
            direccion=f"{sucursal.direccion}, {sucursal.ciudad}",
            hasta=paquete.retiro_hasta,
            lo_retira="remitente" if paquete.en_devolucion else "destinatario",
        )

    def _ubicacion_publica(self, paquete):
        if paquete.estado not in (EstadoPaqueteEnum.EN_REPARTO.value, EstadoPaqueteEnum.EN_TRANSITO.value):
            return None
        for asignacion in paquete.recorrido_asignaciones:
            recorrido = asignacion.recorrido
            if (recorrido.estado != EstadoRecorridoEnum.EN_CURSO.value
                    or asignacion.estado_en_recorrido != EstadoRecorridoPaqueteEnum.PENDIENTE.value
                    or not recorrido.repartidor.activo):
                continue
            posicion = recorrido.repartidor.posicion_actual
            if posicion and posicion.recorrido_id == recorrido.id:
                return UbicacionData(latitud=posicion.latitud, longitud=posicion.longitud,
                                     actualizado_at=posicion.actualizado_at)
        return None
