from typing import Any

from app.application.interfaces.repositorio_envios import IRepositorioEnvios
from app.application.interfaces.repositorio_sucursales import IRepositorioSucursales
from app.contracts.sucursales import (
    GuardarSucursalRequest,
    ListarSucursalesAdminResponse,
    ListarSucursalesResponse,
    OpcionesRetiroData,
    OpcionesRetiroResponse,
    PaqueteRetiroData,
    SucursalAdminData,
    SucursalAdminResponse,
    SucursalData,
    SucursalRetiroData,
)
from app.core.exceptions import DuplicateEntryException, NotFoundException
from app.domain.rules.codigos_rules import normalizar_token_seguimiento
from app.domain.rules.retiro_rules import (
    envio_habilita_retiro_en_sucursal,
    paquete_disponible_en_sucursal,
)


class ServicioSucursales:
    """Servicio de consulta pública del catálogo de sucursales y de las opciones
    de retiro de un envío (HU03 y HU09)."""

    def __init__(
        self,
        repositorio_sucursales: IRepositorioSucursales,
        repositorio_envios: IRepositorioEnvios,
    ):
        self.repo_sucursales = repositorio_sucursales
        self.repo_envios = repositorio_envios

    async def listar_sucursales(
        self,
        provincia: str | None = None,
        ciudad: str | None = None,
    ) -> ListarSucursalesResponse:
        """Devuelve el catálogo de sucursales, opcionalmente filtrado por zona.

        Sin filtros se comporta igual que antes de HU09 (catálogo completo, que
        es lo que consume el selector de retiro en sucursal de HU03).
        """
        sucursales = await self.repo_sucursales.listar_todas(provincia=provincia, ciudad=ciudad)
        # Las inactivas no reciben envíos nuevos: no se ofrecen en el catálogo público.
        return ListarSucursalesResponse(
            data=[self._mapear_sucursal(s) for s in sucursales if getattr(s, "activa", True)]
        )

    # --- Administración (Superadministrador) ---

    async def listar_admin(self) -> ListarSucursalesAdminResponse:
        usuarios = await self.repo_sucursales.contar_usuarios()
        return ListarSucursalesAdminResponse(
            data=[self._mapear_admin(s, usuarios.get(s.id, 0)) for s in await self.repo_sucursales.listar_todas()]
        )

    async def crear_sucursal(self, datos: GuardarSucursalRequest) -> SucursalAdminResponse:
        await self._nombre_libre(datos.nombre)
        sucursal = await self.repo_sucursales.guardar(self.repo_sucursales.nueva(**datos.model_dump()))
        return SucursalAdminResponse(message="Sucursal creada.", data=self._mapear_admin(sucursal, 0))

    async def actualizar_sucursal(self, id: int, datos: GuardarSucursalRequest) -> SucursalAdminResponse:
        sucursal = await self.repo_sucursales.obtener_por_id(id)
        if not sucursal:
            raise NotFoundException("No existe esa sucursal.")
        await self._nombre_libre(datos.nombre, id)
        for campo, valor in datos.model_dump().items():
            setattr(sucursal, campo, valor)
        sucursal = await self.repo_sucursales.guardar(sucursal)
        usuarios = await self.repo_sucursales.contar_usuarios()
        return SucursalAdminResponse(message="Sucursal actualizada.", data=self._mapear_admin(sucursal, usuarios.get(id, 0)))

    async def _nombre_libre(self, nombre: str, id: int | None = None) -> None:
        existente = await self.repo_sucursales.obtener_por_nombre(nombre)
        if existente and existente.id != id:
            raise DuplicateEntryException(
                message="Ya hay una sucursal con ese nombre.",
                errors=[{"field": "nombre", "message": "Elegí otro nombre."}],
            )

    def _mapear_admin(self, sucursal: Any, usuarios: int) -> SucursalAdminData:
        return SucursalAdminData(
            **self._mapear_sucursal(sucursal).model_dump(), activa=getattr(sucursal, "activa", True), usuarios=usuarios,
        )

    async def obtener_opciones_retiro(self, token: str) -> OpcionesRetiroResponse:
        """Devuelve las sucursales donde se puede retirar el envío de ese token (HU09).

        Cubre el Escenario 1 de HU09: desde la experiencia pública, sin iniciar
        sesión, quien espera un paquete consulta dónde puede retirarlo. Si el
        envío es a domicilio, responde `200` con `aplica_retiro = false` y el
        motivo, en vez de un error: el token es válido, solo que ese envío no se
        retira por sucursal.
        """
        envio = await self.repo_envios.obtener_por_token(normalizar_token_seguimiento(token))
        if not envio:
            raise NotFoundException(
                "No se encontró un envío asociado a ese código de seguimiento."
            )

        aplica, motivo = envio_habilita_retiro_en_sucursal(envio.tipo_entrega)
        if not aplica:
            return OpcionesRetiroResponse(
                data=OpcionesRetiroData(
                    token_seguimiento=envio.token_seguimiento,
                    tipo_entrega=envio.tipo_entrega,
                    aplica_retiro=False,
                    motivo_no_aplica=motivo,
                )
            )

        sucursal_asignada = envio.sucursal_destino
        sucursales_disponibles = await self._armar_sucursales_disponibles(sucursal_asignada)

        return OpcionesRetiroResponse(
            data=OpcionesRetiroData(
                token_seguimiento=envio.token_seguimiento,
                tipo_entrega=envio.tipo_entrega,
                aplica_retiro=True,
                motivo_no_aplica=None,
                sucursal_asignada=(
                    self._mapear_sucursal_retiro(sucursal_asignada, es_asignada=True)
                    if sucursal_asignada
                    else None
                ),
                sucursales_disponibles=sucursales_disponibles,
                paquetes=[
                    PaqueteRetiroData(
                        numero_paquete=p.numero_paquete,
                        descripcion=p.descripcion,
                        estado=p.estado,
                        disponible_para_retirar=paquete_disponible_en_sucursal(p.estado),
                    )
                    for p in envio.paquetes
                ],
            )
        )

    async def _armar_sucursales_disponibles(
        self,
        sucursal_asignada: Any | None,
    ) -> list[SucursalRetiroData]:
        """Arma la lista de puntos de retiro, con la sucursal asignada primero.

        Además de la sucursal elegida al registrar el envío, se listan las otras
        sucursales de la misma ciudad como referencia de la red cercana (marcadas
        con `es_sucursal_asignada = false`): el paquete solo se entrega en la
        asignada, pero el destinatario necesita ubicarla entre las de su zona.
        """
        if not sucursal_asignada:
            return []

        sucursales_ciudad = await self.repo_sucursales.listar_todas(
            provincia=sucursal_asignada.provincia,
            ciudad=sucursal_asignada.ciudad,
        )

        disponibles = [self._mapear_sucursal_retiro(sucursal_asignada, es_asignada=True)]
        disponibles.extend(
            self._mapear_sucursal_retiro(s, es_asignada=False)
            for s in sucursales_ciudad
            if s.id != sucursal_asignada.id
        )
        return disponibles

    def _mapear_sucursal(self, sucursal: Any) -> SucursalData:
        """Convierte el modelo de sucursal al contrato público del catálogo."""
        return SucursalData(
            id=sucursal.id,
            nombre=sucursal.nombre,
            provincia=sucursal.provincia,
            ciudad=sucursal.ciudad,
            direccion=sucursal.direccion,
            latitud=sucursal.latitud,
            longitud=sucursal.longitud,
        )

    def _mapear_sucursal_retiro(self, sucursal: Any, es_asignada: bool) -> SucursalRetiroData:
        """Igual que `_mapear_sucursal`, marcando si es el punto de retiro del envío."""
        return SucursalRetiroData(
            id=sucursal.id,
            nombre=sucursal.nombre,
            provincia=sucursal.provincia,
            ciudad=sucursal.ciudad,
            direccion=sucursal.direccion,
            latitud=sucursal.latitud,
            longitud=sucursal.longitud,
            es_sucursal_asignada=es_asignada,
        )
