import {
  AlertTriangle,
  Boxes,
  CircleCheckBig,
  Clock3,
  LayoutDashboard,
  MessageSquareWarning,
  MonitorDot,
  PackageSearch,
  Store,
  Warehouse,
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
      { id: 'monitor-overview', label: 'Panel general', path: '/monitor', icon: LayoutDashboard, description: 'Paquetes por etapa, actividad del día, recorridos y lo que requiere atención.', keywords: 'resumen tablero indicadores' },
      { id: 'monitor-all', label: 'Todos los paquetes', path: '/monitor/paquetes', icon: Boxes, description: 'Listado completo con búsqueda, filtros por sucursal, entrega y fechas, y exportación.', keywords: 'listado buscar exportar csv excel' },
      { id: 'monitor-pending', label: 'Pendientes de ingreso', path: '/monitor/pendientes', icon: Clock3, description: 'Registrados por el cliente que todavía no llegaron a una terminal.', keywords: 'pendiente recepción' },
      { id: 'monitor-warehouse', label: 'En depósito', path: '/monitor/deposito', icon: Warehouse, description: 'Paquetes en terminales y sucursales, listos para salir o en espera.', keywords: 'sucursal terminal stock' },
      { id: 'monitor-transit', label: 'En camino', path: '/monitor/en-camino', icon: Truck, description: 'En tránsito entre sucursales o en reparto a domicilio, con su repartidor.', keywords: 'reparto tránsito repartidor' },
      { id: 'monitor-pickup', label: 'Para retirar', path: '/monitor/para-retirar', icon: Store, description: 'Disponibles en la sucursal elegida, esperando que el cliente los retire.', keywords: 'retiro sucursal' },
      { id: 'monitor-delivered', label: 'Entregados', path: '/monitor/entregados', icon: CircleCheckBig, description: 'Entregados a domicilio o retirados, con quién recibió y la firma.', keywords: 'entregado firma retirado' },
      { id: 'monitor-incidents', label: 'Incidencias', path: '/monitor/incidencias', icon: AlertTriangle, description: 'Visitas fallidas, paquetes sin recorrido y con reclamos en curso.', keywords: 'no entregados fallida alerta problema' },
      { id: 'monitor-claims', label: 'Reclamos', path: '/monitor/reclamos', icon: MessageSquareWarning, description: 'Bandeja de reclamos de los clientes: revisar, responder y cerrar.', keywords: 'reclamo queja demora daño extravío' },
      { id: 'monitor-trace', label: 'Trazabilidad', path: '/monitor/trazabilidad', icon: PackageSearch, description: 'Todo lo que pasó con un paquete: estados, recorridos, entregas, avisos y reclamos.', keywords: 'historial auditoría buscar paquete escanear' },
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

/** Ruta activa de una subsección: la portada solo coincide con su ruta exacta. */
export function isChildActive(child: NavigationChild, module: NavigationModule, pathname: string) {
  if (child.path === module.path) return pathname === module.path
  return pathname === child.path || pathname.startsWith(`${child.path}/`)
}
