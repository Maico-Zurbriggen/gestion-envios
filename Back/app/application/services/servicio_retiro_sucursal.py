from datetime import datetime, timezone
from typing import Any, Optional
import uuid

from app.application.interfaces.repositorio_entregas import IRepositorioEntregas
from app.application.interfaces.servicio_retiro_sucursal import IServicioRetiroSucursal
from app.contracts.sucursal_retiro import (
    DestinatarioRetiroInfo,
    RegistrarRetiroRequest,
    RegistrarRetiroResponse,
    RequisitosRetiroInfo,
    RetiroRegistradoData,
    ValidarRetiroData,
    ValidarRetiroResponse,
)
from app.contracts.sucursales import SucursalData
from app.core.exceptions import NotFoundException, ValidationException
from app.domain.constants.estados_logistica import (
    EstadoPaqueteEnum,
    ResultadoEventoEntregaEnum,
    TipoEventoEntregaEnum,
    TipoRetiroEnum,
)
from app.domain.rules.retiro_rules import (
    evaluar_disponibilidad_retiro,
    validar_requisitos_retiro,
)
from app.infrastructure.db.models import EventoEntregaModel, HistorialEstadoPaqueteModel, SucursalModel


class ServicioRetiroSucursal(IServicioRetiroSucursal):
    """Servicio de aplicación para la gestión de retiros de paquetes en sucursal (HU13)."""

    def __init__(self, repositorio_entregas: IRepositorioEntregas):
        self.repo_entregas = repositorio_entregas

    async def validar_retiro(self, id_o_codigo: str) -> ValidarRetiroResponse:
        """Verifica la existencia, estado y condiciones previas para el retiro de un paquete."""
        paquete = await self.repo_entregas.buscar_paquete_por_id_o_codigo(id_o_codigo)
        if not paquete:
            raise NotFoundException(
                message=f"No se encontró un paquete con el identificador '{id_o_codigo}'."
            )

        disponible, motivo = evaluar_disponibilidad_retiro(paquete.estado)

        envio = paquete.envio
        sucursal_destino_data = self._mapear_sucursal(envio.sucursal_destino) if envio and envio.sucursal_destino else None
        sucursal_actual_data = self._mapear_sucursal(paquete.sucursal_actual) if paquete.sucursal_actual else None

        return ValidarRetiroResponse(
            data=ValidarRetiroData(
                paquete_id=paquete.id,
                numero_paquete=paquete.numero_paquete,
                descripcion=paquete.descripcion,
                peso_kg=paquete.peso_kg,
                estado_actual=paquete.estado,
                disponible_para_retiro=disponible,
                motivo_no_disponible=motivo,
                tipo_entrega=envio.tipo_entrega if envio else "sucursal",
                sucursal_destino=sucursal_destino_data,
                sucursal_actual=sucursal_actual_data,
                datos_destinatario=DestinatarioRetiroInfo(
                    nombre=envio.destinatario_nombre if envio else "Desconocido",
                    telefono=envio.destinatario_telefono if envio else "Desconocido",
                    email=envio.destinatario_email if envio else "Desconocido",
                ),
                requisitos_retiro=RequisitosRetiroInfo(),
            )
        )

    async def registrar_retiro(
        self,
        id_o_codigo: str,
        datos: RegistrarRetiroRequest,
        usuario_admin: Any,
    ) -> RegistrarRetiroResponse:
        """Valida identidades/autorizaciones y registra el retiro físico del paquete."""
        paquete = await self.repo_entregas.buscar_paquete_por_id_o_codigo(id_o_codigo)
        if not paquete:
            raise NotFoundException(
                message=f"No se encontró un paquete con el identificador '{id_o_codigo}'."
            )

        # 1. Validación de estado previo apto para retiro
        disponible, motivo = evaluar_disponibilidad_retiro(paquete.estado)
        if not disponible:
            raise ValidationException(
                message="El paquete no está en un estado válido para retiro en sucursal.",
                errors=[{"field": "estado", "message": motivo or "Estado no apto para retiro."}],
            )

        # 2. Validación de reglas de negocio según tipo de retiro
        tercero_dict = datos.tercero_autorizado.model_dump() if datos.tercero_autorizado else None
        errores_reglas = validar_requisitos_retiro(
            tipo_retiro=datos.tipo_retiro,
            destinatario_mayor_16=datos.destinatario_mayor_16,
            documento_tipo=datos.documento_presentado.tipo,
            documento_numero=datos.documento_presentado.numero,
            tercero_datos=tercero_dict,
        )

        if errores_reglas:
            raise ValidationException(
                message="No se cumplen las condiciones o requisitos documentales para el retiro.",
                errors=errores_reglas,
            )

        envio = paquete.envio
        nuevo_estado = EstadoPaqueteEnum.ENTREGADO_EN_SUCURSAL.value
        ahora = datetime.now(timezone.utc)

        # 3. Determinación de datos del receptor
        if datos.tipo_retiro == TipoRetiroEnum.TITULAR.value:
            receptor_nombre = envio.destinatario_nombre if envio else "Titular"
            receptor_documento = datos.documento_presentado.numero.strip()
            es_autorizado = False
            detalle_obs = f"Retiro presencial por titular ({datos.documento_presentado.tipo} {receptor_documento})."
        else:
            receptor_nombre = datos.tercero_autorizado.nombre_completo.strip()  # type: ignore
            receptor_documento = datos.tercero_autorizado.documento.strip()  # type: ignore
            es_autorizado = True
            detalle_obs = (
                f"Retiro por tercero autorizado: {receptor_nombre} (Doc: {receptor_documento}). "
                f"Se constató copia del DNI del titular y autorización firmada."
            )

        if datos.observaciones and datos.observaciones.strip():
            detalle_obs += f" Obs: {datos.observaciones.strip()}"

        sucursal_id = paquete.sucursal_actual_id or (envio.sucursal_destino_id if envio else None)

        # 4. Creación de entidades de auditoría y entrega
        evento_entrega = EventoEntregaModel(
            id=uuid.uuid4(),
            paquete_id=paquete.id,
            tipo_evento=TipoEventoEntregaEnum.RETIRO_SUCURSAL.value,
            resultado=ResultadoEventoEntregaEnum.EXITOSO.value,
            receptor_nombre=receptor_nombre,
            receptor_documento=receptor_documento,
            es_autorizado=es_autorizado,
            documento_destinatario_verificado=True,
            firma_imagen=None,
            firma_content_type=None,
            motivo_fallo=None,
            usuario_registro_id=usuario_admin.id,
            sucursal_id=sucursal_id,
            created_at=ahora,
        )

        historial_estado = HistorialEstadoPaqueteModel(
            paquete_id=paquete.id,
            estado_anterior=paquete.estado,
            estado_nuevo=nuevo_estado,
            usuario_id=usuario_admin.id,
            sucursal_id=sucursal_id,
            observacion=detalle_obs,
            created_at=ahora,
        )

        # 5. Persistencia transaccional
        paquete_actualizado = await self.repo_entregas.registrar_retiro_paquete(
            paquete_id=paquete.id,
            nuevo_estado=nuevo_estado,
            evento_entrega=evento_entrega,
            historial_estado=historial_estado,
            sucursal_actual_id=sucursal_id,
        )

        return RegistrarRetiroResponse(
            data=RetiroRegistradoData(
                paquete_id=paquete_actualizado.id,
                numero_paquete=paquete_actualizado.numero_paquete,
                estado=paquete_actualizado.estado,
                tipo_retiro=datos.tipo_retiro,
                receptor_nombre=receptor_nombre,
                receptor_documento=receptor_documento,
                es_autorizado=es_autorizado,
                usuario_administrativo_id=usuario_admin.id,
                usuario_administrativo_nombre=usuario_admin.nombre,
                fecha_hora_entrega=ahora,
                sucursal_id=sucursal_id,
                observaciones=datos.observaciones,
            )
        )

    def _mapear_sucursal(self, sucursal: Optional[SucursalModel]) -> Optional[SucursalData]:
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
