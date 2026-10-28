import {
  House,
  ClipboardCheck,
  Mails,
  PackagePlus,
  Route,
  Truck,
  ScanBarcode,
  UsersRound,
  Bike,
  type LucideIcon,
} from 'lucide-react'

export type NavigationSection = 'principal' | 'operation' | 'administration'

export interface NavigationModule {
  id: string
  label: string
  /** Nombre corto para la barra inferior del celular. */
  shortLabel: string
  description: string
  path: string
  section: NavigationSection
  icon: LucideIcon
  allowedRoles?: readonly string[]
  showAsQuickAccess?: boolean
  /** Palabras extra para el buscador rápido (Ctrl + K). */
  keywords?: string
}

export const NAVIGATION_SECTIONS: ReadonlyArray<{ id: NavigationSection; label: string }> = [
  { id: 'principal', label: 'Principal' },
  { id: 'operation', label: 'Operación' },
  { id: 'administration', label: 'Administración' },
]

export const NAVIGATION_MODULES: NavigationModule[] = [
  {
    id: 'home',
    label: 'Inicio',
    shortLabel: 'Inicio',
    description: 'Resumen de tu cuenta y accesos disponibles.',
    path: '/',
    section: 'principal',
    icon: House,
    showAsQuickAccess: false,
    keywords: 'panel tablero resumen',
  },
  {
    id: 'create-shipment',
    label: 'Registrar envío',
    shortLabel: 'Nuevo envío',
    description: 'Prepará un envío y generá sus etiquetas para imprimir.',
    path: '/envios/nuevo',
    section: 'principal',
    icon: PackagePlus,
    showAsQuickAccess: true,
    keywords: 'nuevo paquete planilla etiqueta alta',
  },
  {
    id: 'tracking',
    label: 'Seguir envío',
    shortLabel: 'Seguir',
    description: 'Consultá el estado de tus paquetes con el código de seguimiento.',
    path: '/seguimiento',
    section: 'principal',
    icon: Route,
    showAsQuickAccess: true,
    keywords: 'token rastrear estado reclamo',
  },
  {
    id: 'terminal-reception',
    label: 'Recibir paquetes',
    shortLabel: 'Recibir',
    description: 'Identificá un paquete y confirmá su ingreso físico a la terminal.',
    path: '/terminal/recepcion',
    section: 'operation',
    icon: ScanBarcode,
    allowedRoles: ['VENDEDOR', 'ADMINISTRATIVO', 'SUPERADMIN'],
    showAsQuickAccess: true,
    keywords: 'escanear lector código de barras recepción terminal',
  },
  {
    id: 'pickup',
    label: 'Registrar retiro',
    shortLabel: 'Retiros',
    description: 'Verificá la identidad y registrá la entrega de un paquete en sucursal.',
    path: '/sucursal/retiros',
    section: 'operation',
    icon: ClipboardCheck,
    allowedRoles: ['ADMINISTRATIVO', 'SUPERADMIN'],
    showAsQuickAccess: true,
    keywords: 'sucursal entrega documento',
  },
  {
    id: 'delivery-routes',
    label: 'Gestionar recorridos',
    shortLabel: 'Recorridos',
    description: 'Generá recorridos, organizá las paradas y revisá los paquetes sin asignar.',
    path: '/recorridos',
    section: 'operation',
    icon: Truck,
    allowedRoles: ['ADMINISTRATIVO', 'SUPERADMIN'],
    showAsQuickAccess: true,
    keywords: 'reparto repartidores mapa alertas logística',
  },
  {
    id: 'driver-delivery',
    label: 'Mi reparto',
    shortLabel: 'Mi reparto',
    description: 'Consultá tus recorridos, compartí ubicación y registrá entregas o visitas.',
    path: '/reparto',
    section: 'operation',
    icon: Bike,
    allowedRoles: ['REPARTIDOR'],
    showAsQuickAccess: true,
    keywords: 'entregas firma gps recorrido',
  },
  {
    id: 'users',
    label: 'Usuarios',
    shortLabel: 'Usuarios',
    description: 'Registrá, editá y administrá al personal, sus roles y su acceso.',
    path: '/admin/usuarios',
    section: 'administration',
    icon: UsersRound,
    allowedRoles: ['SUPERADMIN'],
    showAsQuickAccess: true,
    keywords: 'empleados personal roles contraseña alta baja',
  },
  {
    id: 'email-templates',
    label: 'Correos a clientes',
    shortLabel: 'Correos',
    description: 'Personalizá los correos de seguimiento y avisos que reciben los clientes.',
    path: '/admin/correos',
    section: 'administration',
    icon: Mails,
    allowedRoles: ['ADMINISTRATIVO', 'SUPERADMIN'],
    showAsQuickAccess: true,
    keywords: 'gmail email mensajes plantillas notificaciones',
  },
]

export function getAccessibleModules(role?: string | null) {
  return NAVIGATION_MODULES.filter(
    (module) =>
      !module.allowedRoles?.length ||
      (role ? module.allowedRoles.includes(role) : false),
  )
}
