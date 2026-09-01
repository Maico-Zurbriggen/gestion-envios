import {
  House,
  PackagePlus,
  Route,
  UserPlus,
  type LucideIcon,
} from 'lucide-react'

export interface NavigationModule {
  id: string
  label: string
  description: string
  path: string
  section: 'general' | 'administration'
  icon: LucideIcon
  allowedRoles?: readonly string[]
  showAsQuickAccess?: boolean
}

export const NAVIGATION_SECTIONS = [
  { id: 'general', label: 'General' },
  { id: 'administration', label: 'Administración' },
] as const

export const NAVIGATION_MODULES: NavigationModule[] = [
  {
    id: 'home',
    label: 'Inicio',
    description: 'Resumen de tu cuenta y accesos disponibles.',
    path: '/',
    section: 'general',
    icon: House,
    showAsQuickAccess: false,
  },
  {
    id: 'create-shipment',
    label: 'Registrar envío',
    description: 'Prepará un envío y generá sus etiquetas para imprimir.',
    path: '/envios/nuevo',
    section: 'general',
    icon: PackagePlus,
    showAsQuickAccess: true,
  },
  {
    id: 'tracking',
    label: 'Seguir envío',
    description: 'Consultá el estado de tus paquetes con el código de seguimiento.',
    path: '/seguimiento',
    section: 'general',
    icon: Route,
    showAsQuickAccess: true,
  },
  {
    id: 'create-user',
    label: 'Registrar usuario',
    description: 'Creá empleados y asignales su rol operativo.',
    path: '/admin/usuarios/nuevo',
    section: 'administration',
    icon: UserPlus,
    allowedRoles: ['SUPERADMIN'],
    showAsQuickAccess: true,
  },
]

export function getAccessibleModules(role?: string | null) {
  return NAVIGATION_MODULES.filter(
    (module) =>
      !module.allowedRoles?.length ||
      (role ? module.allowedRoles.includes(role) : false),
  )
}
