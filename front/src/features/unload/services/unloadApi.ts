import { operationalRequest } from '../../../shared/services/operationalApi'

export type ReadResult = 'CORRECTO' | 'SOBRANTE' | 'DESCONOCIDO'

interface ApiIncomingRoute {
  recorrido_id: string
  fecha: string
  estado: string
  repartidor_nombre: string
  sucursal_origen: string
  esperados: number
  verificados: number
  control_id: string | null
  control_estado: 'EN_CURSO' | 'CERRADO' | null
}

interface ApiControl {
  id: string
  estado: 'EN_CURSO' | 'CERRADO'
  recorrido: { id: string; fecha: string; estado: string; repartidor_nombre: string; sucursal_origen: string }
  sucursal: { id: number; nombre: string }
  esperados: Array<{
    paquete_id: string
    numero_paquete: string
    descripcion: string
    destinatario_nombre: string
    tipo_entrega: string
    estado: string
    estado_etiqueta: string
    verificado: boolean
    verificado_at: string | null
    verificado_por: string | null
  }>
  sobrantes: Array<{ codigo: string; resultado: ReadResult; detalle: string | null; usuario_nombre: string | null; created_at: string }>
  total_esperados: number
  verificados: number
  faltantes: number
  resumen: string
  iniciado_por: string | null
  created_at: string
  cerrado_por: string | null
  cerrado_at: string | null
  observaciones: string | null
}

export interface IncomingRoute {
  routeId: string
  date: string
  status: string
  driverName: string
  originBranch: string
  expected: number
  verified: number
  controlId: string | null
  controlStatus: 'EN_CURSO' | 'CERRADO' | null
}

export interface UnloadControl {
  id: string
  status: 'EN_CURSO' | 'CERRADO'
  route: { id: string; date: string; status: string; driverName: string; originBranch: string }
  branch: { id: number; name: string }
  expected: Array<{
    id: string
    code: string
    description: string
    recipientName: string
    deliveryType: string
    statusLabel: string
    verified: boolean
    verifiedAt: string | null
    verifiedBy: string | null
  }>
  extras: Array<{ code: string; result: ReadResult; detail: string | null; userName: string | null; createdAt: string }>
  totalExpected: number
  verified: number
  missing: number
  summary: string
  startedBy: string | null
  createdAt: string
  closedBy: string | null
  closedAt: string | null
  notes: string | null
}

export interface ReadOutcome {
  code: string
  result: ReadResult
  repeated: boolean
  message: string
  control: UnloadControl
}

function mapControl(control: ApiControl): UnloadControl {
  return {
    id: control.id,
    status: control.estado,
    route: {
      id: control.recorrido.id,
      date: control.recorrido.fecha,
      status: control.recorrido.estado,
      driverName: control.recorrido.repartidor_nombre,
      originBranch: control.recorrido.sucursal_origen,
    },
    branch: { id: control.sucursal.id, name: control.sucursal.nombre },
    expected: control.esperados.map((item) => ({
      id: item.paquete_id,
      code: item.numero_paquete,
      description: item.descripcion,
      recipientName: item.destinatario_nombre,
      deliveryType: item.tipo_entrega,
      statusLabel: item.estado_etiqueta,
      verified: item.verificado,
      verifiedAt: item.verificado_at,
      verifiedBy: item.verificado_por,
    })),
    extras: control.sobrantes.map((item) => ({
      code: item.codigo,
      result: item.resultado,
      detail: item.detalle,
      userName: item.usuario_nombre,
      createdAt: item.created_at,
    })),
    totalExpected: control.total_esperados,
    verified: control.verificados,
    missing: control.faltantes,
    summary: control.resumen,
    startedBy: control.iniciado_por,
    createdAt: control.created_at,
    closedBy: control.cerrado_por,
    closedAt: control.cerrado_at,
    notes: control.observaciones,
  }
}

const BASE = '/terminal/descargas'
const NOT_FOUND = { notFound: 'Ese control de descarga ya no existe. Volvé a la lista de recorridos.' }

export async function getIncomingRoutes(branchId: number, token: string): Promise<IncomingRoute[]> {
  const { data } = await operationalRequest<{ data: ApiIncomingRoute[] }>(`${BASE}/recorridos?sucursal_id=${branchId}`, token)
  return data.map((route) => ({
    routeId: route.recorrido_id,
    date: route.fecha,
    status: route.estado,
    driverName: route.repartidor_nombre,
    originBranch: route.sucursal_origen,
    expected: route.esperados,
    verified: route.verificados,
    controlId: route.control_id,
    controlStatus: route.control_estado,
  }))
}

export async function startUnloadControl(routeId: string, branchId: number, token: string) {
  const { data } = await operationalRequest<{ data: ApiControl }>(BASE, token, {
    method: 'POST',
    body: JSON.stringify({ recorrido_id: routeId, sucursal_id: branchId }),
  })
  return mapControl(data)
}

export async function getUnloadControl(id: string, token: string) {
  const { data } = await operationalRequest<{ data: ApiControl }>(`${BASE}/${id}`, token, undefined, NOT_FOUND)
  return mapControl(data)
}

export async function registerRead(id: string, code: string, token: string): Promise<ReadOutcome> {
  const { data } = await operationalRequest<{
    data: { codigo: string; resultado: ReadResult; repetida: boolean; mensaje: string; control: ApiControl }
  }>(`${BASE}/${id}/lecturas`, token, { method: 'POST', body: JSON.stringify({ codigo: code }) }, NOT_FOUND)
  return { code: data.codigo, result: data.resultado, repeated: data.repetida, message: data.mensaje, control: mapControl(data.control) }
}

export async function closeUnloadControl(id: string, notes: string, token: string) {
  const payload = await operationalRequest<{ data: ApiControl; message: string | null }>(
    `${BASE}/${id}/cerrar`,
    token,
    { method: 'POST', body: JSON.stringify({ observaciones: notes.trim() || null }) },
    NOT_FOUND,
  )
  return { control: mapControl(payload.data), message: payload.message }
}
