import {
  Boxes,
  MessageSquareWarning,
  MonitorDot,
  Store,
  House,
  PackagePlus,
  Route,
  Truck,
  ScanBarcode,
  UsersRound,
  Bike,
  Building2,
  type LucideIcon,
} from 'lucide-react'

export type NavigationSection = 'principal' | 'operation' | 'administration'

/** Subsección dentro de un módulo (se despliega en el menú lateral, como en TamboApp). */
export interface NavigationChild {
  id: string
  label: string
  description: string
  path: string
  icon: LucideIcon
  keywords?: string
  /** Otras rutas que pertenecen a la subsección (por ejemplo, el detalle de un elemento). */
  extraPaths?: string[]
}

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
  /** Subsecciones: el módulo se despliega en el menú y su ruta es la portada. */
  children?: NavigationChild[]
}

export const NAVIGATION_SECTIONS: ReadonlyArray<{ id: NavigationSection; label: string }> = [
  { id: 'principal', label: 'Principal' },
  { id: 'operation', label: 'Operación' },
  { id: 'administration', label: 'Administración' },
]

const NAVIGATION_MODULES: NavigationModule[] = [
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
    shortLabel: 'Enviar',
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
    id: 'monitor',
    label: 'Monitor',
    shortLabel: 'Monitor',
    description: 'Todos los paquetes por etapa, la trazabilidad de cada uno y los reclamos.',
    path: '/monitor',
    section: 'operation',
    icon: MonitorDot,
    allowedRoles: ['ADMINISTRATIVO', 'SUPERADMIN'],
    showAsQuickAccess: true,
    keywords: 'tablero administración paquetes estado trazabilidad',
    children: [
      { id: 'monitor-packages', label: 'Paquetes', path: '/monitor/paquetes', icon: Boxes, description: 'Todos los paquetes con pestañas por etapa, búsqueda y filtros.', keywords: 'listado buscar pendientes depósito camino retirar entregados trazabilidad', extraPaths: ['/monitor/trazabilidad'] },
      { id: 'monitor-claims', label: 'Reclamos', path: '/monitor/reclamos', icon: MessageSquareWarning, description: 'Reclamos de los clientes: revisar, responder y cerrar.', keywords: 'reclamo queja demora daño extravío' },
    ],
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
    icon: Store,
    allowedRoles: ['ADMINISTRATIVO', 'SUPERADMIN'],
    showAsQuickAccess: true,
    keywords: 'sucursal entrega documento',
  },
  {
    id: 'delivery-routes',
    label: 'Recorridos',
    shortLabel: 'Recorridos',
    description: 'Armá el reparto del día: repartidor, paquetes y orden de visita, a mano o automático.',
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
    id: 'admin-branches',
    label: 'Sucursales',
    shortLabel: 'Sucursales',
    description: 'Creá y editá sucursales, su dirección de partida y si están activas.',
    path: '/admin/sucursales',
    section: 'administration',
    icon: Building2,
    allowedRoles: ['SUPERADMIN'],
    showAsQuickAccess: false,
    keywords: 'sucursal direccion ubicacion mapa punto de partida habilitar',
  },
]

export function getAccessibleModules(role?: string | null) {
  return NAVIGATION_MODULES.filter(
    (module) =>
      !module.allowedRoles?.length ||
      (role ? module.allowedRoles.includes(role) : false),
  )
}

/** Ruta activa de una subsección: la portada solo coincide con su ruta exacta. */
export function isChildActive(child: NavigationChild, module: NavigationModule, pathname: string) {
  if (child.path === module.path) return pathname === module.path
  return [child.path, ...(child.extraPaths ?? [])].some((path) => pathname === path || pathname.startsWith(`${path}/`))
}
