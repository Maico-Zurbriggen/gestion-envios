export interface ApiAdminBranch {
  id: number
  nombre: string
  provincia: string
  ciudad: string
  direccion: string
  latitud: number | null
  longitud: number | null
  activa: boolean
  usuarios: number
}

/** Sucursal tal como la administra el Superadministrador. */
export interface AdminBranch {
  id: number
  name: string
  province: string
  city: string
  address: string
  latitude: number | null
  longitude: number | null
  active: boolean
  users: number
}

export interface BranchInput {
  name: string
  province: string
  city: string
  address: string
  latitude: number
  longitude: number
  active: boolean
}
