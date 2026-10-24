import uuid
from typing import Any

from app.application.interfaces.repositorio_repartidores import IRepositorioRepartidores
from app.application.interfaces.repositorio_sucursales import IRepositorioSucursales
from app.application.interfaces.servicio_repartidores import IServicioRepartidores
from app.contracts.repartidores import (
    TIPOS_REPARTO_VALIDOS,
    ListarRepartidoresResponse,
    PerfilRepartidorRequest,
    RepartidorData,
    RepartidorResponse,
)
from app.contracts.sucursales import SucursalData
from app.core.exceptions import DuplicateEntryException, NotFoundException, ValidationException
from app.domain.constants.roles import RolEnum
from app.infrastructure.db.models import RepartidorModel, UsuarioModel


class ServicioRepartidores(IServicioRepartidores):
    """Gestión de los perfiles operativos de repartidor (soporte de HU10).

    Sin perfil (sucursal base + tipo de reparto) un repartidor no recibe
    recorridos: la generación automática de HU10 reparte entre los
    repartidores **activos** de la sucursal y del tipo de recorrido pedido.
    """

    def __init__(
        self,
        repositorio_repartidores: IRepositorioRepartidores,
        repositorio_sucursales: IRepositorioSucursales,
    ):
        self.repo_repartidores = repositorio_repartidores
        self.repo_sucursales = repositorio_sucursales

    async def listar(
        self,
        sucursal_id: int | None = None,
        tipo_reparto: str | None = None,
        activo: bool | None = None,
    ) -> ListarRepartidoresResponse:
        tipo = tipo_reparto.strip().upper() if tipo_reparto and tipo_reparto.strip() else None
        if tipo and tipo not in TIPOS_REPARTO_VALIDOS:
            raise ValidationException(
                message="Los filtros indicados no son válidos.",
                errors=[{"field": "tipo_reparto", "message": f"Tipo de reparto inválido: '{tipo_reparto}'."}],
            )

        usuarios = await self.repo_repartidores.listar(sucursal_id=sucursal_id, tipo_reparto=tipo, activo=activo)
        return ListarRepartidoresResponse(total=len(usuarios), data=[self._mapear(u) for u in usuarios])

    async def obtener(self, usuario_id: uuid.UUID) -> RepartidorResponse:
        usuario = await self._obtener_repartidor(usuario_id)
        return RepartidorResponse(data=self._mapear(usuario))

    async def configurar_perfil(self, usuario_id: uuid.UUID, datos: PerfilRepartidorRequest) -> RepartidorResponse:
        usuario = await self._obtener_repartidor(usuario_id)

        sucursal = await self.repo_sucursales.obtener_por_id(datos.sucursal_base_id)
        if not sucursal:
            raise ValidationException(
                message="La sucursal base indicada no existe.",
                errors=[{
                    "field": "sucursal_base_id",
                    "message": f"No existe una sucursal con id {datos.sucursal_base_id}.",
                }],
            )

        perfil: RepartidorModel | None = usuario.repartidor
        cambia_operacion = perfil is not None and (
            perfil.sucursal_base_id != datos.sucursal_base_id
            or perfil.tipo_reparto != datos.tipo_reparto
            or (perfil.activo and not datos.activo)
        )
        # Un recorrido pendiente quedaría inconsistente (otra sucursal u otro tipo de reparto).
        if cambia_operacion and await self.repo_repartidores.tiene_recorridos_activos(usuario.id):
            raise DuplicateEntryException(
                message=(
                    "El repartidor tiene recorridos generados o en curso. Finalizalos, reasignalos o "
                    "eliminalos antes de cambiar su sucursal, su tipo de reparto o desactivarlo."
                ),
                errors=[{"field": "repartidor", "message": "Tiene recorridos activos."}],
            )

        es_alta = perfil is None
        if perfil is None:
            perfil = RepartidorModel(usuario_id=usuario.id)
        perfil.sucursal_base_id = datos.sucursal_base_id
        perfil.tipo_reparto = datos.tipo_reparto
        perfil.activo = datos.activo
        await self.repo_repartidores.guardar_perfil(perfil)

        actualizado = await self._obtener_repartidor(usuario_id)
        return RepartidorResponse(
            message="Perfil de repartidor creado." if es_alta else "Perfil de repartidor actualizado.",
            data=self._mapear(actualizado),
        )

    async def _obtener_repartidor(self, usuario_id: uuid.UUID) -> UsuarioModel:
        usuario = await self.repo_repartidores.obtener_usuario(usuario_id)
        if not usuario:
            raise NotFoundException(f"No existe un usuario con id {usuario_id}.")
        if not usuario.rol or usuario.rol.nombre != RolEnum.REPARTIDOR.value:
            raise ValidationException(
                message="El usuario indicado no tiene rol REPARTIDOR.",
                errors=[{"field": "usuario_id", "message": "Solo se configura perfil de reparto a repartidores."}],
            )
        return usuario

    def _mapear(self, usuario: UsuarioModel) -> RepartidorData:
        perfil: Any = usuario.repartidor
        sucursal = perfil.sucursal_base if perfil else None
        return RepartidorData(
            usuario_id=usuario.id,
            nombre=usuario.nombre,
            dni=usuario.dni,
            email=usuario.email,
            telefono=usuario.telefono,
            estado_usuario=usuario.estado,
            perfil_configurado=perfil is not None,
            sucursal_base=SucursalData(
                id=sucursal.id,
                nombre=sucursal.nombre,
                provincia=sucursal.provincia,
                ciudad=sucursal.ciudad,
                direccion=sucursal.direccion,
                latitud=sucursal.latitud,
                longitud=sucursal.longitud,
            ) if sucursal else None,
            tipo_reparto=perfil.tipo_reparto if perfil else None,
            activo=perfil.activo if perfil else None,
            disponible_para_recorridos=bool(perfil and perfil.activo and usuario.estado == "Activo"),
        )
