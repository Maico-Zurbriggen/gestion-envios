import { operationalRequest } from '../../../shared/services/operationalApi'
import type {
  ApiCreatedUser,
  ApiEmployee,
  ApiEmployeeList,
  ApiRole,
  CreatedUser,
  CreateUserInput,
  CreateUserSuccessResponse,
  Employee,
  EmployeeFilters,
  EmployeeList,
  EmployeeStatus,
  ResetPasswordResult,
  Role,
  RolesSuccessResponse,
  UpdateEmployeeInput,
} from '../types/user.types'

const apiUrl = import.meta.env.VITE_API_URL?.replace(/\/+$/, '')

interface ApiErrorPayload {
  detail?: Array<{ msg?: string }> | string
  message?: string
  errors?: Array<{ message?: string }>
}

export class UsersApiError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'UsersApiError'
  }
}

function mapCreatedUser(user: ApiCreatedUser): CreatedUser {
  return {
    id: user.id,
    name: user.nombre,
    dni: user.dni,
    email: user.email,
    phone: user.telefono,
    status: user.estado,
    role: user.rol,
    temporaryPassword: user.password_temporal,
  }
}

function mapRole(role: ApiRole): Role {
  return {
    id: role.id,
    name: role.nombre,
    description: role.descripcion,
  }
}

function getErrorMessage(
  payload: unknown,
  status: number,
  fallbackMessage = 'No pudimos registrar el usuario. Revisá los datos ingresados.',
) {
  if (payload && typeof payload === 'object') {
    const { detail, errors, message } = payload as ApiErrorPayload

    if (Array.isArray(errors)) {
      const messages = errors.map((error) => error.message).filter(Boolean)
      if (messages.length) return messages.join('. ')
    }

    if (Array.isArray(detail)) {
      const messages = detail.map((error) => error.msg).filter(Boolean)
      if (messages.length) return messages.join('. ')
    }

    if (typeof detail === 'string' && detail) return detail
    if (typeof message === 'string' && message) return message
  }

  if (status === 401) return 'La sesión venció. Volvé a iniciar sesión.'
  if (status === 403) return 'No tenés permisos para registrar usuarios.'
  if (status === 409) return 'Ya existe un usuario con ese DNI o email.'
  if (status >= 500) return 'El servicio no está disponible. Intentá nuevamente.'

  return fallbackMessage
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json()
  } catch {
    return null
  }
}

export async function getRoles(): Promise<Role[]> {
  if (!apiUrl) throw new UsersApiError('No se configuró la URL de la API.')

  let response: Response

  try {
    response = await fetch(`${apiUrl}/roles`, {
      headers: { Accept: 'application/json' },
    })
  } catch {
    throw new UsersApiError(
      'No pudimos conectarnos con el servidor para obtener los roles.',
    )
  }

  const payload = await readJson(response)
  if (!response.ok) {
    throw new UsersApiError(
      getErrorMessage(
        payload,
        response.status,
        'No pudimos obtener los roles disponibles.',
      ),
    )
  }

  const rolesResponse = payload as RolesSuccessResponse
  if (
    rolesResponse?.status !== 'success' ||
    !Array.isArray(rolesResponse.data)
  ) {
    throw new UsersApiError('El servidor devolvió una respuesta inesperada.')
  }

  return rolesResponse.data.map(mapRole)
}

export async function createUser(
  input: CreateUserInput,
  token: string,
): Promise<CreatedUser> {
  if (!apiUrl) throw new UsersApiError('No se configuró la URL de la API.')

  let response: Response

  try {
    response = await fetch(`${apiUrl}/admin/empleados`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        nombre: input.name,
        dni: input.dni,
        email: input.email,
        telefono: input.phone,
        rol_id: input.roleId,
      }),
    })
  } catch {
    throw new UsersApiError(
      'No pudimos conectarnos con el servidor. Intentá nuevamente.',
    )
  }

  const payload = await readJson(response)
  if (!response.ok) {
    throw new UsersApiError(getErrorMessage(payload, response.status))
  }

  const createUserResponse = payload as CreateUserSuccessResponse
  if (createUserResponse?.status !== 'success' || !createUserResponse.data) {
    throw new UsersApiError('El servidor devolvió una respuesta inesperada.')
  }

  return mapCreatedUser(createUserResponse.data)
}

// --- Gestión del personal (listado, edición, estado y blanqueo) -----------

function mapEmployee(employee: ApiEmployee): Employee {
  return {
    id: employee.id,
    name: employee.nombre,
    dni: employee.dni,
    email: employee.email,
    phone: employee.telefono,
    status: employee.estado,
    role: employee.rol,
    roleId: employee.rol_id,
    requiresPasswordChange: employee.requiere_cambio_password,
    createdAt: employee.created_at,
    updatedAt: employee.updated_at,
  }
}

const NOT_FOUND = { notFound: 'El usuario ya no existe. Actualizá el listado.' }

export async function listEmployees(filters: EmployeeFilters, token: string): Promise<EmployeeList> {
  const params = new URLSearchParams()
  if (filters.search?.trim()) params.set('buscar', filters.search.trim())
  if (filters.roleId) params.set('rol_id', String(filters.roleId))
  if (filters.status) params.set('estado', filters.status)
  const query = params.size ? `?${params}` : ''
  const { data } = await operationalRequest<{ data: ApiEmployeeList }>(`/admin/empleados${query}`, token)
  return {
    employees: data.empleados.map(mapEmployee),
    total: data.total,
    summary: {
      total: data.resumen.total,
      active: data.resumen.activos,
      inactive: data.resumen.inactivos,
      byRole: data.resumen.por_rol,
    },
  }
}

export async function updateEmployee(id: string, input: UpdateEmployeeInput, token: string): Promise<Employee> {
  const body: Record<string, string | number> = {}
  if (input.name !== undefined) body.nombre = input.name
  if (input.dni !== undefined) body.dni = input.dni
  if (input.email !== undefined) body.email = input.email
  if (input.phone !== undefined) body.telefono = input.phone
  if (input.roleId !== undefined) body.rol_id = input.roleId
  const { data } = await operationalRequest<{ data: ApiEmployee }>(
    `/admin/empleados/${id}`, token, { method: 'PATCH', body: JSON.stringify(body) }, NOT_FOUND,
  )
  return mapEmployee(data)
}

export async function changeEmployeeStatus(id: string, status: EmployeeStatus, token: string): Promise<{ employee: Employee; message: string }> {
  const payload = await operationalRequest<{ data: ApiEmployee; message: string }>(
    `/admin/empleados/${id}/estado`, token, { method: 'PATCH', body: JSON.stringify({ estado: status }) }, NOT_FOUND,
  )
  return { employee: mapEmployee(payload.data), message: payload.message }
}

export async function resetEmployeePassword(id: string, token: string): Promise<ResetPasswordResult> {
  const { data } = await operationalRequest<{ data: { id: string; nombre: string; password_temporal: string } }>(
    `/admin/empleados/${id}/restablecer-password`, token, { method: 'POST' }, NOT_FOUND,
  )
  return { id: data.id, name: data.nombre, temporaryPassword: data.password_temporal }
}
