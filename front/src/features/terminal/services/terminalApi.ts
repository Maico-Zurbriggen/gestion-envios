import { operationalRequest } from '../../../shared/services/operationalApi'
import type { ApiScannedPackage, Reception, ReceptionInput, ScannedPackage } from '../types/terminal.types'

export async function scanPackage(code: string, token: string, signal?: AbortSignal): Promise<ScannedPackage> {
  const { data } = await operationalRequest<{ status: 'success'; data: ApiScannedPackage }>(`/terminal/paquetes/${encodeURIComponent(code)}/escanear`, token, { signal })
  if (!data?.paquete_id || !data.envio || typeof data.disponible_para_recepcion !== 'boolean') throw new Error('No pudimos leer los datos del paquete.')
  return { id: data.paquete_id, code: data.numero_paquete, description: data.descripcion, weightKg: data.peso_kg,
    dimensions: `${data.largo_cm} × ${data.ancho_cm} × ${data.alto_cm} cm`, notes: data.observaciones,
    status: data.estado_actual, available: data.disponible_para_recepcion, unavailableReason: data.motivo_no_disponible,
    trackingToken: data.envio.token_seguimiento, senderName: data.envio.remitente_nombre, senderDocument: data.envio.remitente_documento,
    recipientName: data.envio.destinatario_nombre, destination: data.envio.destino }
}

export async function receivePackage(input: ReceptionInput, token: string): Promise<Reception> {
  const { data } = await operationalRequest<{ status: 'success'; data: { numero_paquete: string; estado: string; sucursal_nombre: string; fecha_hora_recepcion: string } }>(`/terminal/paquetes/${encodeURIComponent(input.code)}/recepcionar`, token, {
    method: 'POST', body: JSON.stringify({ sucursal_id: input.branchId, observaciones: input.notes.trim() || null }),
  })
  if (!data?.numero_paquete || !data.fecha_hora_recepcion) throw new Error('No pudimos leer la confirmación. Consultá el paquete antes de volver a confirmar.')
  return { code: data.numero_paquete, status: data.estado, branchName: data.sucursal_nombre, receivedAt: data.fecha_hora_recepcion }
}
