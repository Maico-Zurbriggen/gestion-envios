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

export type EmployeeStatus = 'Activo' | 'Inactivo'

export interface ApiEmployee {
  id: string
  nombre: string
  dni: string
  email: string
  telefono: string
  estado: EmployeeStatus
  rol: string
  rol_id: number
  requiere_cambio_password: boolean
  created_at: string | null
  updated_at: string | null
}

export interface ApiEmployeeList {
  empleados: ApiEmployee[]
  total: number
  resumen: {
    total: number
    activos: number
    inactivos: number
    por_rol: Record<string, number>
  }
}

export interface Employee {
  id: string
  name: string
  dni: string
  email: string
  phone: string
  status: EmployeeStatus
  role: string
  roleId: number
  requiresPasswordChange: boolean
  createdAt: string | null
  updatedAt: string | null
}

export interface EmployeeSummary {
  total: number
  active: number
  inactive: number
  byRole: Record<string, number>
}

export interface EmployeeList {
  employees: Employee[]
  total: number
  summary: EmployeeSummary
}

export interface EmployeeFilters {
  search?: string
  roleId?: number | null
  status?: EmployeeStatus | null
}

export type UpdateEmployeeInput = Partial<CreateUserInput>

export interface ResetPasswordResult {
  id: string
  name: string
  temporaryPassword: string
}
