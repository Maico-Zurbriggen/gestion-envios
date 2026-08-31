import type {
  ApiErrorResponse,
  ApiUser,
  AuthSession,
  LoginCredentials,
  LoginSuccessResponse,
} from '../types/auth.types'

const apiUrl = import.meta.env.VITE_API_URL?.replace(/\/+$/, '')

export class AuthApiError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'AuthApiError'
  }
}

function mapUser(user: ApiUser): AuthSession['user'] {
  return {
    id: user.id,
    name: user.nombre,
    dni: user.dni,
    email: user.email,
    role: user.rol,
    requiresPasswordChange: user.requiere_cambio_password,
  }
}

function getApiErrorMessage(payload: unknown, status: number) {
  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const { detail } = payload as ApiErrorResponse

    if (Array.isArray(detail)) {
      const messages = detail
        .map((issue) => issue.msg)
        .filter((message): message is string => Boolean(message))

      if (messages.length) return messages.join('. ')
    }

    if (typeof detail === 'string' && detail) return detail
  }

  if (status === 401) return 'El DNI o la contraseña son incorrectos.'
  if (status >= 500) return 'El servicio no está disponible. Intentá nuevamente.'

  return 'No pudimos iniciar sesión. Revisá los datos ingresados.'
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json()
  } catch {
    return null
  }
}

export async function login(credentials: LoginCredentials): Promise<AuthSession> {
  if (!apiUrl) {
    throw new AuthApiError('No se configuró la URL de la API.')
  }

  let response: Response

  try {
    response = await fetch(`${apiUrl}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(credentials),
    })
  } catch {
    throw new AuthApiError(
      'No pudimos conectarnos con el servidor. Intentá nuevamente.',
    )
  }

  const payload = await readJson(response)

  if (!response.ok) {
    throw new AuthApiError(getApiErrorMessage(payload, response.status))
  }

  const loginResponse = payload as LoginSuccessResponse

  if (
    loginResponse?.status !== 'success' ||
    !loginResponse.data?.token ||
    !loginResponse.data?.user
  ) {
    throw new AuthApiError('El servidor devolvió una respuesta inesperada.')
  }

  return {
    token: loginResponse.data.token,
    user: mapUser(loginResponse.data.user),
  }
}
