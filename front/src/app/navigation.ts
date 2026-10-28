import {
  AlertTriangle,
  Boxes,
  LayoutDashboard,
  MessageSquareWarning,
  MonitorDot,
  Store,
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
    id: 'monitor',
    label: 'Monitor',
    shortLabel: 'Monitor',
    description: 'Todos los paquetes por etapa, incidencias, reclamos y la trazabilidad completa de cada uno.',
    path: '/monitor',
    section: 'operation',
    icon: MonitorDot,
    allowedRoles: ['ADMINISTRATIVO', 'SUPERADMIN'],
    showAsQuickAccess: true,
    keywords: 'tablero administración paquetes estado trazabilidad',
    children: [
      { id: 'monitor-overview', label: 'Resumen', path: '/monitor', icon: LayoutDashboard, description: 'Indicadores, paquetes por etapa, lo que requiere atención y la actividad del día.', keywords: 'panel tablero indicadores resumen' },
      { id: 'monitor-packages', label: 'Paquetes', path: '/monitor/paquetes', icon: Boxes, description: 'Todos los paquetes con pestañas por etapa, búsqueda, filtros y exportación.', keywords: 'listado buscar pendientes depósito camino retirar entregados exportar csv trazabilidad', extraPaths: ['/monitor/trazabilidad'] },
      { id: 'monitor-incidents', label: 'Incidencias', path: '/monitor/incidencias', icon: AlertTriangle, description: 'Visitas fallidas, faltantes en la descarga, paquetes sin recorrido y con reclamos.', keywords: 'no entregados fallida alerta problema faltante' },
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
    id: 'unload-control',
    label: 'Carga y descarga',
    shortLabel: 'Carga',
    description: 'Escaneá lo que sube al vehículo antes de salir y lo que baja al llegar, y compará con lo previsto.',
    path: '/terminal/descarga',
    section: 'operation',
    icon: ClipboardCheck,
    allowedRoles: ['VENDEDOR', 'ADMINISTRATIVO', 'SUPERADMIN'],
    showAsQuickAccess: true,
    keywords: 'descarga llegada camión sucursal destino escanear faltante sobrante',
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

/** Ruta activa de una subsección: la portada solo coincide con su ruta exacta. */
export function isChildActive(child: NavigationChild, module: NavigationModule, pathname: string) {
  if (child.path === module.path) return pathname === module.path
  return [child.path, ...(child.extraPaths ?? [])].some((path) => pathname === path || pathname.startsWith(`${path}/`))
}
