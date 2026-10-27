from datetime import UTC, datetime
from typing import Any

from app.application.interfaces.repositorio_recepciones import IRepositorioRecepciones
from app.application.interfaces.repositorio_sucursales import IRepositorioSucursales
from app.application.interfaces.servicio_recepcion_terminal import IServicioRecepcionTerminal
from app.contracts.recepcion_terminal import (
    EnvioResumenRecepcion,
    EscanearPaqueteResponse,
    PaqueteEscaneadoData,
    PaqueteRecepcionadoData,
    RecepcionarPaqueteRequest,
    RecepcionarPaqueteResponse,
)
from app.contracts.sucursales import SucursalData
from app.core.exceptions import DuplicateEntryException, NotFoundException, ValidationException
from app.domain.constants.estados_logistica import EstadoPaqueteEnum
from app.domain.rules.destino_rules import (
    formatear_destino_domicilio,
    formatear_destino_sucursal,
)
from app.domain.rules.recepcion_rules import (
    ESTADOS_VALIDOS_PARA_RECEPCION,
    estado_tras_recepcion,
    evaluar_disponibilidad_recepcion,
    normalizar_codigo_escaneado,
    validar_codigo_escaneado,
)
from app.domain.rules.retiro_rules import TIPO_ENTREGA_DOMICILIO
from app.infrastructure.db.models import HistorialEstadoPaqueteModel, PaqueteModel, SucursalModel


class ServicioRecepcionTerminal(IServicioRecepcionTerminal):
    """Servicio de aplicación de la recepción de paquetes en terminal (HU06).

    Implementa el Escenario 1 de HU06: el vendedor escanea el código de barras
    de la planilla impresa, el sistema identifica el paquete precargado en HU03
    y permite dejarlo registrado en la terminal como listo para su envío.
    """

    def __init__(
        self,
        repositorio_recepciones: IRepositorioRecepciones,
        repositorio_sucursales: IRepositorioSucursales,
    ):
        self.repo_recepciones = repositorio_recepciones
        self.repo_sucursales = repositorio_sucursales

    async def escanear_paquete(self, codigo: str) -> EscanearPaqueteResponse:
        """Identifica el paquete a partir del código escaneado, sin modificarlo.

        Es una consulta de solo lectura: devuelve los datos del paquete y de su
        envío para que el vendedor confirme en pantalla que coinciden con lo que
        tiene en el mostrador antes de asentar la recepción.
        """
        paquete = await self._obtener_paquete(codigo)
        disponible, motivo = evaluar_disponibilidad_recepcion(paquete.estado)

        return EscanearPaqueteResponse(
            data=self._mapear_paquete_escaneado(paquete, disponible, motivo)
        )

    async def recepcionar_paquete(
        self,
        codigo: str,
        datos: RecepcionarPaqueteRequest,
        usuario_vendedor: Any,
    ) -> RecepcionarPaqueteResponse:
        """Registra el ingreso físico del paquete a la terminal.

        Pasa el estado a `EN_SUCURSAL_ORIGEN` (o a `LISTO_PARA_RETIRO` si se
        recibe en la misma sucursal elegida para el retiro), fija la sucursal
        donde quedó ubicado y agrega la fila al historial de estados, todo en
        una sola transacción.
        """
        paquete = await self._obtener_paquete(codigo)

        # 1. El paquete tiene que estar pendiente de ingreso: no se puede
        #    recibir dos veces ni reingresar uno ya entregado.
        disponible, motivo = evaluar_disponibilidad_recepcion(paquete.estado)
        if not disponible:
            raise ValidationException(
                message="El paquete no se puede recibir en la terminal en su estado actual.",
                errors=[{"field": "estado", "message": motivo or "Estado no apto para recepción."}],
            )

        # 2. La terminal informada debe existir en el catálogo de sucursales.
        sucursal = await self.repo_sucursales.obtener_por_id(datos.sucursal_id)
        if not sucursal:
            raise ValidationException(
                message="La sucursal indicada para la recepción no existe.",
                errors=[{
                    "field": "sucursal_id",
                    "message": f"No existe una sucursal con id {datos.sucursal_id}.",
                }],
            )

        estado_anterior = paquete.estado
        envio = paquete.envio
        nuevo_estado = estado_tras_recepcion(envio.tipo_entrega, envio.sucursal_destino_id, sucursal.id)
        ahora = datetime.now(UTC)

        # 3. Auditoría: una fila por cada cambio de estado, con quién y dónde.
        observacion = f"Paquete recibido en terminal {sucursal.nombre} mediante escaneo del código de barras."
        if nuevo_estado == EstadoPaqueteEnum.LISTO_PARA_RETIRO.value:
            observacion += " Es la sucursal elegida para el retiro: queda disponible para el destinatario."
        if datos.observaciones and datos.observaciones.strip():
            observacion += f" Obs: {datos.observaciones.strip()}"

        historial_estado = HistorialEstadoPaqueteModel(
            paquete_id=paquete.id,
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado,
            usuario_id=usuario_vendedor.id,
            sucursal_id=sucursal.id,
            latitud=sucursal.latitud,
            longitud=sucursal.longitud,
            observacion=observacion,
            created_at=ahora,
        )

        # 4. Persistencia transaccional del estado, la ubicación y el historial.
        paquete_actualizado = await self.repo_recepciones.registrar_recepcion_paquete(
            paquete_id=paquete.id,
            nuevo_estado=nuevo_estado,
            sucursal_id=sucursal.id,
            historial_estado=historial_estado,
            estados_previos=ESTADOS_VALIDOS_PARA_RECEPCION,
        )
        if paquete_actualizado is None:
            raise DuplicateEntryException(
                message="El paquete ya fue recibido por otra operación. Volvé a escanearlo para ver su estado.",
                errors=[{"field": "estado", "message": "Recepción ya registrada."}],
            )

        return RecepcionarPaqueteResponse(
            data=PaqueteRecepcionadoData(
                paquete_id=paquete_actualizado.id,
                numero_paquete=paquete_actualizado.numero_paquete,
                estado_anterior=estado_anterior,
                estado=paquete_actualizado.estado,
                sucursal_id=sucursal.id,
                sucursal_nombre=sucursal.nombre,
                usuario_receptor_id=usuario_vendedor.id,
                usuario_receptor_nombre=usuario_vendedor.nombre,
                fecha_hora_recepcion=ahora,
                observaciones=datos.observaciones,
                token_seguimiento=paquete_actualizado.envio.token_seguimiento,
            )
        )

    async def _obtener_paquete(self, codigo: str) -> PaqueteModel:
        """Valida el formato del código escaneado y resuelve el paquete.

        Centraliza el camino común de los dos endpoints: formato inválido ->
        `400 VALIDATION_ERROR`; código bien formado pero inexistente ->
        `404 NOT_FOUND`.
        """
        errores_formato = validar_codigo_escaneado(codigo)
        if errores_formato:
            raise ValidationException(
                message="El código de barras escaneado no es válido.",
                errors=errores_formato,
            )

        codigo_normalizado = normalizar_codigo_escaneado(codigo)
        paquete = await self.repo_recepciones.buscar_paquete_por_codigo(codigo_normalizado)
        if not paquete:
            raise NotFoundException(
                message=(
                    f"No se encontró un paquete precargado con el código '{codigo_normalizado}'. "
                    "Verificá que la planilla corresponda a un envío registrado en el sistema."
                )
            )
        return paquete

    def _mapear_paquete_escaneado(
        self,
        paquete: PaqueteModel,
        disponible: bool,
        motivo: str | None,
    ) -> PaqueteEscaneadoData:
        """Arma la respuesta del escaneo a partir del paquete y su envío."""
        envio = paquete.envio

        return PaqueteEscaneadoData(
            paquete_id=paquete.id,
            numero_paquete=paquete.numero_paquete,
            descripcion=paquete.descripcion,
            peso_kg=paquete.peso_kg,
            largo_cm=paquete.largo_cm,
            ancho_cm=paquete.ancho_cm,
            alto_cm=paquete.alto_cm,
            observaciones=paquete.observaciones,
            estado_actual=paquete.estado,
            disponible_para_recepcion=disponible,
            motivo_no_disponible=motivo,
            fecha_registro=paquete.created_at,
            sucursal_actual=self._mapear_sucursal(paquete.sucursal_actual),
            envio=EnvioResumenRecepcion(
                envio_id=envio.id,
                token_seguimiento=envio.token_seguimiento,
                remitente_nombre=envio.remitente_nombre,
                remitente_documento=envio.remitente_documento,
                remitente_telefono=envio.remitente_telefono,
                destinatario_nombre=envio.destinatario_nombre,
                destinatario_telefono=envio.destinatario_telefono,
                tipo_entrega=envio.tipo_entrega,
                destino=self._armar_destino(envio),
                sucursal_destino=self._mapear_sucursal(envio.sucursal_destino),
            ),
        )

    def _armar_destino(self, envio: Any) -> str:
        """Arma el destino como un único texto legible para la pantalla del vendedor.

        Usa el mismo formateador que la vista pública de HU04
        (`domain/rules/destino_rules.py`), para que las dos pantallas muestren
        idéntico el destino de un mismo envío.
        """
        if envio.tipo_entrega == TIPO_ENTREGA_DOMICILIO:
            return formatear_destino_domicilio(
                direccion=envio.direccion_destino,
                ciudad=envio.ciudad_destino,
                provincia=envio.provincia_destino,
            )

        sucursal = envio.sucursal_destino
        return formatear_destino_sucursal(
            nombre=sucursal.nombre if sucursal else None,
            direccion=sucursal.direccion if sucursal else None,
            ciudad=sucursal.ciudad if sucursal else None,
            provincia=sucursal.provincia if sucursal else None,
        )

    def _mapear_sucursal(self, sucursal: SucursalModel | None) -> SucursalData | None:
        """Convierte el modelo de sucursal al contrato público, tolerando `None`."""
        if not sucursal:
            return None
        return SucursalData(
            id=sucursal.id,
            nombre=sucursal.nombre,
            provincia=sucursal.provincia,
            ciudad=sucursal.ciudad,
            direccion=sucursal.direccion,
            latitud=sucursal.latitud,
            longitud=sucursal.longitud,
        )
