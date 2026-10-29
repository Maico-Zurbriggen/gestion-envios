export interface LoginCredentials {
  dni: string
  password: string
}

export interface LoginTokenCredentials {
  token: string
}

export interface ApiBranchAccess {
  id: number
  nombre: string
  ciudad: string
  provincia: string
  direccion: string
  activa: boolean
}

export interface ApiUser {
  id: string
  nombre: string
  dni: string
  email: string
  rol: string
  requiere_cambio_password: boolean
  sucursales?: ApiBranchAccess[]
}

export interface LoginSuccessResponse {
  status: 'success'
  data: {
    token: string
    user: ApiUser
  }
}

export interface LoginRequiresPasswordChangeResponse {
  status: 'requires_password_change'
  message: string
  data: {
    temp_token: string
    requiere_cambio_password: true
  }
}

export interface PasswordChangeChallenge {
  token: string
  dni: string
}

export interface ChangePasswordCredentials {
  currentPassword: string
  newPassword: string
  passwordConfirmation: string
}

export interface ChangePasswordSuccessResponse {
  status: 'success'
  message: string
  data: {
    auth_token: string
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
  message?: string
  errors?: Array<{
    field: string
    message: string
  }>
}

/** Sucursal en la que el usuario puede trabajar. */
export interface AuthBranch {
  id: number
  name: string
  city: string
  province: string
  address: string
  active: boolean
}

export interface AuthUser {
  id: string
  name: string | null
  dni: string
  email: string | null
  role: string
  requiresPasswordChange: boolean
  branches: AuthBranch[]
}

export interface AuthSession {
  token: string
  user: AuthUser
}

export type LoginResult =
  | {
      type: 'authenticated'
      session: AuthSession
    }
  | {
      type: 'passwordChangeRequired'
      challenge: PasswordChangeChallenge
    }
