import { operationalRequest } from '../../../shared/services/operationalApi'
import type {
  ApiPickupBranch,
  PickupBranch,
  PickupValidation,
  PickupValidationResponse,
  RegisteredPickup,
  RegisterPickupInput,
  RegisterPickupResponse,
} from '../types/pickup.types'

const NOT_FOUND = 'No encontramos un paquete con ese código.'

function mapBranch(branch: ApiPickupBranch | null): PickupBranch | null {
  return branch ? { id: branch.id, name: branch.nombre, address: branch.direccion, city: branch.ciudad } : null
}

export async function validatePickup(code: string, token: string, signal?: AbortSignal): Promise<PickupValidation> {
  const { data } = await operationalRequest<PickupValidationResponse>(
    `/sucursal/paquetes/${encodeURIComponent(code)}/validar-retiro`, token, { signal }, { notFound: NOT_FOUND },
  )
  if (!data?.paquete_id || !data.numero_paquete || typeof data.disponible_para_retiro !== 'boolean' || !data.datos_destinatario) {
    throw new Error('No pudimos leer los datos del paquete.')
  }
  return {
    packageId: data.paquete_id,
    packageNumber: data.numero_paquete,
    description: data.descripcion,
    weightKg: data.peso_kg,
    status: data.estado_actual,
    available: data.disponible_para_retiro,
    unavailableReason: data.motivo_no_disponible,
    deliveryType: data.tipo_entrega,
    destinationBranch: mapBranch(data.sucursal_destino),
    currentBranch: mapBranch(data.sucursal_actual),
    recipient: { name: data.datos_destinatario.nombre, phone: data.datos_destinatario.telefono, email: data.datos_destinatario.email },
    requirements: { recipient: data.requisitos_retiro.titular, authorizedPerson: data.requisitos_retiro.tercero_autorizado },
    isReturn: Boolean(data.es_devolucion),
    pickupUntil: data.retiro_hasta ?? null,
    pickupBranch: mapBranch(data.sucursal_retiro ?? data.sucursal_destino),
  }
}

export async function registerPickup(input: RegisterPickupInput, token: string): Promise<RegisteredPickup> {
  const { data } = await operationalRequest<RegisterPickupResponse>(
    `/sucursal/paquetes/${encodeURIComponent(input.packageId)}/registrar-retiro`, token, {
      method: 'POST',
      body: JSON.stringify({
        tipo_retiro: input.type,
        documento_presentado: { tipo: input.documentType, numero: input.documentNumber },
        destinatario_mayor_16: input.recipientOver16,
        sucursal_id: input.branchId,
        receptor_fecha_nacimiento: input.receiverBirthDate,
        documento_original_verificado: input.documentReviewed,
        // El documento presentado por un tercero es el propio: debe coincidir con el de la autorización.
        tercero_autorizado: input.type === 'TERCERO_AUTORIZADO' ? {
          nombre_completo: input.authorizedName,
          documento: input.documentNumber,
          posee_copia_dni_titular: input.hasRecipientDocumentCopy,
          posee_nota_autorizacion: input.hasSignedAuthorization,
        } : null,
        observaciones: input.notes.trim() || null,
      }),
    }, { notFound: NOT_FOUND },
  )
  if (!data?.numero_paquete || !data.fecha_hora_entrega) {
    throw new Error('No pudimos leer la confirmación. Buscá el paquete antes de volver a registrar el retiro.')
  }
  return {
    packageNumber: data.numero_paquete,
    status: data.estado,
    recipientName: data.receptor_nombre,
    recipientDocument: data.receptor_documento,
    operatorName: data.usuario_administrativo_nombre,
    deliveredAt: data.fecha_hora_entrega,
  }
}
