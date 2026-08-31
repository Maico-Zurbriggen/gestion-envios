export interface LoginCredentials {
  dni: string
  password: string
}

export interface ApiUser {
  id: string
  nombre: string
  dni: string
  email: string
  rol: string
  requiere_cambio_password: boolean
}

export interface LoginSuccessResponse {
  status: 'success'
  data: {
    token: string
    user: ApiUser
  }
}

export interface ApiValidationIssue {
  loc: Array<string | number>
  msg: string
  type: string
  input?: unknown
  ctx?: Record<string, unknown>
}

export interface ApiErrorResponse {
  detail: ApiValidationIssue[] | string
}

export interface AuthUser {
  id: string
  name: string
  dni: string
  email: string
  role: string
  requiresPasswordChange: boolean
}

export interface AuthSession {
  token: string
  user: AuthUser
}
