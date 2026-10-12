from app.application.interfaces.repositorio_envios import IRepositorioEnvios
from app.contracts.seguimiento import PaqueteSeguimientoData, SeguimientoData, SeguimientoResponse
from app.core.exceptions import NotFoundException
from app.domain.rules.destino_rules import (
    formatear_destino_domicilio,
    formatear_destino_sucursal,
)


class ServicioSeguimiento:
    """Servicio de consulta pública de seguimiento de envíos por token (HU04)."""

    def __init__(self, repositorio_envios: IRepositorioEnvios):
        self.repo_envios = repositorio_envios

    async def obtener_seguimiento(self, token: str) -> SeguimientoResponse:
        envio = await self.repo_envios.obtener_por_token(token)
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
