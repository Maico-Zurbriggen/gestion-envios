export interface CreateUserInput {
  name: string
  dni: string
  email: string
  phone: string
  roleId: number
}

export interface ApiRole {
  id: number
  nombre: string
  descripcion: string
}

export interface RolesSuccessResponse {
  status: 'success'
  data: ApiRole[]
}

export interface Role {
  id: number
  name: string
  description: string
}

export interface ApiCreatedUser {
  id: string
  nombre: string
  dni: string
  email: string
  telefono: string
  estado: string
  rol: string
  password_temporal: string
}

export interface CreateUserSuccessResponse {
  status: 'success'
  message: string
  data: ApiCreatedUser
}

export interface CreatedUser {
  id: string
  name: string
  dni: string
  email: string
  phone: string
  status: string
  role: string
  temporaryPassword: string
}
