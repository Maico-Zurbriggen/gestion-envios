from app.application.interfaces.repositorio_envios import IRepositorioEnvios
from app.application.interfaces.repositorio_sucursales import IRepositorioSucursales
from app.contracts.envios import (
    CrearEnvioRequest,
    CrearEnvioResponse,
    EnvioCreadoData,
    PaqueteCreadoData,
)
from app.contracts.sucursales import SucursalData
from app.core.exceptions import AppException, ValidationException
from app.domain.constants.error_codes import ErrorCodes
from app.domain.rules.codigos_rules import generar_numero_paquete, generar_token_seguimiento
from app.domain.rules.paquete_rules import validar_paquete
from app.infrastructure.db.models import EnvioModel, PaqueteModel

MAX_INTENTOS_GENERACION_CODIGO = 5


class ServicioEnvios:
    """Servicio que implementa el registro público de envíos con uno o más paquetes (HU03)."""

    def __init__(
        self,
        repositorio_envios: IRepositorioEnvios,
        repositorio_sucursales: IRepositorioSucursales,
    ):
        self.repo_envios = repositorio_envios
        self.repo_sucursales = repositorio_sucursales

    async def crear_envio(self, datos: CrearEnvioRequest) -> CrearEnvioResponse:
        """Registra un Envío con sus Paquetes asociados (HU03 - Escenarios 1 y 2)."""
        sucursal = None
        if datos.tipo_entrega == "sucursal":
            sucursal = await self.repo_sucursales.obtener_por_id(datos.sucursal_destino_id)
            if not sucursal:
                raise ValidationException(
                    message="La sucursal seleccionada no es válida.",
                    errors=[
                        {
                            "field": "sucursal_destino_id",
                            "message": f"No existe una sucursal con ID {datos.sucursal_destino_id}.",
                        }
                    ],
                )

        errores_paquetes = []
        for indice, paquete in enumerate(datos.paquetes):
            errores = validar_paquete(
                peso_kg=paquete.peso_kg,
                largo_cm=paquete.largo_cm,
                ancho_cm=paquete.ancho_cm,
                alto_cm=paquete.alto_cm,
            )
            for error in errores:
                errores_paquetes.append(
                    {"field": f"paquetes[{indice}].{error['field']}", "message": error["message"]}
                )

        if errores_paquetes:
            raise ValidationException(
                message="Uno o más paquetes no cumplen con las restricciones de peso o dimensiones.",
                errors=errores_paquetes,
            )

        token_seguimiento = await self._generar_token_unico()

        paquetes_modelo = []
        numeros_asignados: set[str] = set()
        for paquete in datos.paquetes:
            numero_paquete = await self._generar_numero_paquete_unico(numeros_asignados)
            numeros_asignados.add(numero_paquete)
            paquetes_modelo.append(
                PaqueteModel(
                    numero_paquete=numero_paquete,
                    descripcion=paquete.descripcion.strip(),
                    peso_kg=paquete.peso_kg,
                    largo_cm=paquete.largo_cm,
                    ancho_cm=paquete.ancho_cm,
                    alto_cm=paquete.alto_cm,
                    observaciones=paquete.observaciones.strip() if paquete.observaciones else None,
                    estado="Pendiente",
                )
            )

        nuevo_envio = EnvioModel(
            remitente_nombre=datos.remitente_nombre.strip(),
            remitente_documento=datos.remitente_documento.strip(),
            remitente_telefono=datos.remitente_telefono.strip(),
            remitente_email=datos.remitente_email.strip().lower(),
            destinatario_nombre=datos.destinatario_nombre.strip(),
            destinatario_telefono=datos.destinatario_telefono.strip(),
            destinatario_email=datos.destinatario_email.strip().lower(),
            tipo_entrega=datos.tipo_entrega,
            provincia_destino=datos.provincia_destino.strip() if datos.provincia_destino else None,
            ciudad_destino=datos.ciudad_destino.strip() if datos.ciudad_destino else None,
            direccion_destino=datos.direccion_destino.strip() if datos.direccion_destino else None,
            latitud_destino=datos.latitud_destino,
            longitud_destino=datos.longitud_destino,
            sucursal_destino_id=datos.sucursal_destino_id if datos.tipo_entrega == "sucursal" else None,
            terminos_aceptados=datos.terminos_aceptados,
            token_seguimiento=token_seguimiento,
            paquetes=paquetes_modelo,
        )

        envio_creado = await self.repo_envios.crear(nuevo_envio)

        return CrearEnvioResponse(
            data=EnvioCreadoData(
                id=envio_creado.id,
                token_seguimiento=envio_creado.token_seguimiento,
                remitente_nombre=envio_creado.remitente_nombre,
                remitente_documento=envio_creado.remitente_documento,
                remitente_telefono=envio_creado.remitente_telefono,
                remitente_email=envio_creado.remitente_email,
                destinatario_nombre=envio_creado.destinatario_nombre,
                destinatario_telefono=envio_creado.destinatario_telefono,
                destinatario_email=envio_creado.destinatario_email,
                tipo_entrega=envio_creado.tipo_entrega,
                provincia_destino=envio_creado.provincia_destino,
                ciudad_destino=envio_creado.ciudad_destino,
                direccion_destino=envio_creado.direccion_destino,
                latitud_destino=envio_creado.latitud_destino,
                longitud_destino=envio_creado.longitud_destino,
                sucursal_destino=(
                    SucursalData(
                        id=envio_creado.sucursal_destino.id,
                        nombre=envio_creado.sucursal_destino.nombre,
                        provincia=envio_creado.sucursal_destino.provincia,
                        ciudad=envio_creado.sucursal_destino.ciudad,
                        direccion=envio_creado.sucursal_destino.direccion,
                        latitud=envio_creado.sucursal_destino.latitud,
                        longitud=envio_creado.sucursal_destino.longitud,
                    )
                    if envio_creado.sucursal_destino
                    else None
                ),
                paquetes=[
                    PaqueteCreadoData(
                        id=p.id,
                        numero_paquete=p.numero_paquete,
                        descripcion=p.descripcion,
                        peso_kg=p.peso_kg,
                        largo_cm=p.largo_cm,
                        ancho_cm=p.ancho_cm,
                        alto_cm=p.alto_cm,
                        observaciones=p.observaciones,
                        estado=p.estado,
                    )
                    for p in envio_creado.paquetes
                ],
                created_at=envio_creado.created_at,
            )
        )

    async def _generar_token_unico(self) -> str:
        for _ in range(MAX_INTENTOS_GENERACION_CODIGO):
            candidato = generar_token_seguimiento()
            if not await self.repo_envios.existe_token(candidato):
                return candidato
        raise AppException(
            message="No se pudo generar un token de seguimiento único. Intente nuevamente.",
            code=ErrorCodes.INTERNAL_ERROR,
            status_code=500,
        )

    async def _generar_numero_paquete_unico(self, ya_asignados: set[str]) -> str:
        for _ in range(MAX_INTENTOS_GENERACION_CODIGO):
            candidato = generar_numero_paquete()
            if candidato not in ya_asignados and not await self.repo_envios.existe_numero_paquete(candidato):
                return candidato
        raise AppException(
            message="No se pudo generar un número de paquete único. Intente nuevamente.",
            code=ErrorCodes.INTERNAL_ERROR,
            status_code=500,
        )
