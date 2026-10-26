from app.application.interfaces.repositorio_envios import IRepositorioEnvios
from app.contracts.reparto import UbicacionData
from app.contracts.seguimiento import (
    EventoSeguimientoData,
    PaqueteSeguimientoData,
    SeguimientoData,
    SeguimientoResponse,
)
from app.core.exceptions import NotFoundException
from app.domain.constants.estados_logistica import EstadoPaqueteEnum, EstadoRecorridoEnum, EstadoRecorridoPaqueteEnum
from app.domain.rules.codigos_rules import normalizar_token_seguimiento
from app.domain.rules.destino_rules import (
    formatear_destino_domicilio,
    formatear_destino_sucursal,
)


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
                    descripcion={
                        EstadoPaqueteEnum.ENTREGADO.value: "Entrega a domicilio completada.",
                        EstadoPaqueteEnum.ENTREGA_FALLIDA.value: "Aviso de visita: entrega no concretada.",
                        EstadoPaqueteEnum.EN_SUCURSAL_DESTINO.value: "Llegada a la sucursal de destino.",
                    }.get(h.estado_nuevo, "Actualización del estado del paquete."),
                ) for h in sorted(p.historial_estados, key=lambda h: (h.created_at, h.id))],
                ubicacion_repartidor=self._ubicacion_publica(p),
            )
            for p in envio.paquetes
        ]

        return SeguimientoResponse(
            data=SeguimientoData(
                token_seguimiento=envio.token_seguimiento,
                destino=destino,
                latitud_destino=latitud_destino,
                longitud_destino=longitud_destino,
                paquetes=paquetes,
            )
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
