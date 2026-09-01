import type {
  ApiErrorResponse,
  ApiUser,
  AuthSession,
  ChangePasswordCredentials,
  ChangePasswordSuccessResponse,
  LoginCredentials,
  LoginRequiresPasswordChangeResponse,
  LoginResult,
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
  if (payload && typeof payload === 'object') {
    const { detail, errors, message } = payload as ApiErrorResponse

    if (Array.isArray(errors)) {
      const messages = errors
        .map((issue) => issue.message)
        .filter((errorMessage): errorMessage is string => Boolean(errorMessage))

      if (messages.length) return messages.join('. ')
    }

    if (Array.isArray(detail)) {
      const messages = detail
        .map((issue) => issue.msg)
        .filter((message): message is string => Boolean(message))

      if (messages.length) return messages.join('. ')
    }

    if (typeof detail === 'string' && detail) return detail
    if (typeof message === 'string' && message) return message
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

export async function login(credentials: LoginCredentials): Promise<LoginResult> {
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

  const passwordChangeResponse = payload as LoginRequiresPasswordChangeResponse

  if (
    passwordChangeResponse?.status === 'requires_password_change' &&
    passwordChangeResponse.data?.temp_token
  ) {
    return {
      type: 'passwordChangeRequired',
      challenge: {
        token: passwordChangeResponse.data.temp_token,
        dni: credentials.dni,
      },
    }
  }

  const loginResponse = payload as LoginSuccessResponse

  if (
    loginResponse?.status !== 'success' ||
    !loginResponse.data?.token ||
    !loginResponse.data?.user
  ) {
    throw new AuthApiError('El servidor devolvió una respuesta inesperada.')
  }

  const session = {
    token: loginResponse.data.token,
    user: mapUser(loginResponse.data.user),
  }

  if (session.user.requiresPasswordChange) {
    return {
      type: 'passwordChangeRequired',
      challenge: { token: session.token, dni: credentials.dni },
    }
  }

  return {
    type: 'authenticated',
    session,
  }
}

export async function changePassword(
  credentials: ChangePasswordCredentials,
  token: string,
): Promise<{ authToken: string; message: string }> {
  if (!apiUrl) {
    throw new AuthApiError('No se configuró la URL de la API.')
  }

  let response: Response

  try {
    response = await fetch(`${apiUrl}/auth/cambiar-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        password_actual: credentials.currentPassword,
        nueva_password: credentials.newPassword,
        confirmacion_password: credentials.passwordConfirmation,
      }),
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

  const changePasswordResponse = payload as ChangePasswordSuccessResponse
  if (
    changePasswordResponse?.status !== 'success' ||
    !changePasswordResponse.data?.auth_token
  ) {
    throw new AuthApiError('El servidor devolvió una respuesta inesperada.')
  }

  return {
    authToken: changePasswordResponse.data.auth_token,
    message: changePasswordResponse.message,
  }
}
