import { operationalRequest } from '../../../shared/services/operationalApi'
import type { AdminBranch, ApiAdminBranch, BranchInput } from '../types/branch.types'

function mapBranch(branch: ApiAdminBranch): AdminBranch {
  return {
    id: branch.id,
    name: branch.nombre,
    province: branch.provincia,
    city: branch.ciudad,
    address: branch.direccion,
    latitude: branch.latitud,
    longitude: branch.longitud,
    active: branch.activa,
    users: branch.usuarios,
  }
}

function toApi(input: BranchInput) {
  return {
    nombre: input.name,
    provincia: input.province,
    ciudad: input.city,
    direccion: input.address,
    latitud: input.latitude,
    longitud: input.longitude,
    activa: input.active,
  }
}

export async function listAdminBranches(token: string): Promise<AdminBranch[]> {
  const { data } = await operationalRequest<{ data: ApiAdminBranch[] }>('/admin/sucursales', token)
  return data.map(mapBranch)
}

export async function saveBranch(id: number | null, input: BranchInput, token: string) {
  const { data, message } = await operationalRequest<{ data: ApiAdminBranch; message: string }>(
    id ? `/admin/sucursales/${id}` : '/admin/sucursales',
    token,
    { method: id ? 'PUT' : 'POST', body: JSON.stringify(toApi(input)) },
    { notFound: 'La sucursal ya no existe. Actualizá el listado.' },
  )
  return { branch: mapBranch(data), message }
}
