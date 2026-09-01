import type {
  ApiCreatedUser,
  CreatedUser,
  CreateUserInput,
  CreateUserSuccessResponse,
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

function getErrorMessage(payload: unknown, status: number) {
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

  return 'No pudimos registrar el usuario. Revisá los datos ingresados.'
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json()
  } catch {
    return null
  }
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
