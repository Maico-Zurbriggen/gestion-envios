from pydantic import Field

from app.contracts.common import ApiModel


class SucursalData(ApiModel):
    """Catálogo público de sucursales: alimenta el selector de "retiro en
    sucursal" de HU03 y la vista de sucursales disponibles de HU09."""

    id: int
    nombre: str
    provincia: str
    ciudad: str
    direccion: str
    latitud: float | None = None
    longitud: float | None = None


class ListarSucursalesResponse(ApiModel):
    status: str = "success"
    data: list[SucursalData]


# --- HU09: sucursales disponibles para retiro de un envío concreto ---


class SucursalRetiroData(SucursalData):
    """Sucursal ofrecida como punto de retiro para un envío puntual (HU09).

    Agrega al catálogo base la marca `es_sucursal_asignada`, que distingue la
    sucursal elegida al registrar el envío (HU03) de las demás sucursales de la
    misma ciudad, que se listan solo como referencia de la red.
    """

    es_sucursal_asignada: bool = False


class PaqueteRetiroData(ApiModel):
    """Estado de cada paquete del envío, para saber si ya se puede ir a buscar."""

    numero_paquete: str
    descripcion: str
    estado: str
    disponible_para_retirar: bool


class RequisitosRetiroPublico(ApiModel):
    """Qué tiene que llevar quien va a retirar, informado desde la vista pública.

    Replica el texto que el mostrador de HU13 exige al registrar el retiro, para
    que el destinatario no se entere de los requisitos recién en la ventanilla.
    """

    titular: str = "Presentar documento de identidad original y acreditar ser mayor de 16 años."
    tercero_autorizado: str = (
        "Presentar documento de identidad propio, copia del documento del titular "
        "y constancia/formulario de autorización de retiro firmada por el destinatario."
    )


class OpcionesRetiroData(ApiModel):
    """Opciones de retiro de un envío consultadas con el token de seguimiento.

    `aplica_retiro` es `False` cuando el envío es a domicilio: en ese caso
    `sucursal_asignada` y `sucursales_disponibles` vienen vacíos y
    `motivo_no_aplica` explica por qué, en vez de devolver un error — el token
    es válido, simplemente ese envío no se retira por sucursal.
    """

    token_seguimiento: str
    tipo_entrega: str
    aplica_retiro: bool
    motivo_no_aplica: str | None = None
    sucursal_asignada: SucursalRetiroData | None = None
    sucursales_disponibles: list[SucursalRetiroData] = Field(default_factory=list)
    paquetes: list[PaqueteRetiroData] = Field(default_factory=list)
    requisitos_retiro: RequisitosRetiroPublico = Field(default_factory=RequisitosRetiroPublico)


class OpcionesRetiroResponse(ApiModel):
    """Respuesta pública de las sucursales disponibles para retiro (HU09)."""

    status: str = "success"
    data: OpcionesRetiroData
