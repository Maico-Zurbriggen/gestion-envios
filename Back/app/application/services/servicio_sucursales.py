from app.application.interfaces.repositorio_sucursales import IRepositorioSucursales
from app.contracts.sucursales import ListarSucursalesResponse, SucursalData


class ServicioSucursales:
    """Servicio de consulta del catálogo público de sucursales."""

    def __init__(self, repositorio_sucursales: IRepositorioSucursales):
        self.repo_sucursales = repositorio_sucursales

    async def listar_sucursales(self) -> ListarSucursalesResponse:
        sucursales = await self.repo_sucursales.listar_todas()
        return ListarSucursalesResponse(
            data=[
                SucursalData(
                    id=s.id,
                    nombre=s.nombre,
                    provincia=s.provincia,
                    ciudad=s.ciudad,
                    direccion=s.direccion,
                    latitud=s.latitud,
                    longitud=s.longitud,
                )
                for s in sucursales
            ]
        )
