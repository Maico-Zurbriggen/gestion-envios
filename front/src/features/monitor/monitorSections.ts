import { AlertTriangle, Boxes, CircleCheckBig, Clock3, Store, Truck, Warehouse } from 'lucide-react'
import type { PackagesSectionConfig } from './pages/MonitorPackagesPage'

/** Subsecciones de listado del monitor, por ruta relativa a `/monitor`. */
export const MONITOR_SECTIONS: Record<string, PackagesSectionConfig> = {
  paquetes: {
    title: 'Todos los paquetes',
    description: 'Cada paquete registrado, en cualquier etapa. Buscá, filtrá por sucursal, tipo de entrega o fechas y exportá el resultado.',
    icon: Boxes,
    group: 'TODOS',
    tabs: [
      { id: 'TODOS', label: 'Todos' },
      { id: 'PENDIENTES', label: 'Pendientes' },
      { id: 'EN_DEPOSITO', label: 'En depósito' },
      { id: 'EN_CAMINO', label: 'En camino' },
      { id: 'PARA_RETIRAR', label: 'Para retirar' },
      { id: 'ENTREGADOS', label: 'Entregados' },
      { id: 'NO_ENTREGADOS', label: 'Visita fallida' },
    ],
    empty: 'Todavía no se registró ningún envío.',
    related: [{ label: 'Incidencias', to: '/monitor/incidencias' }, { label: 'Trazabilidad', to: '/monitor/trazabilidad' }],
  },
  pendientes: {
    title: 'Pendientes de ingreso',
    description: 'El cliente los registró pero todavía no los entregó en una terminal. Se reciben escaneando la etiqueta en Recibir paquetes.',
    icon: Clock3,
    group: 'PENDIENTES',
    empty: 'No hay paquetes esperando ingresar a una terminal.',
    related: [{ label: 'Recibir paquetes', to: '/terminal/recepcion' }, { label: 'En depósito', to: '/monitor/deposito' }],
  },
  deposito: {
    title: 'En depósito',
    description: 'Paquetes que están físicamente en una terminal o sucursal, esperando su recorrido o su próximo tramo.',
    icon: Warehouse,
    group: 'EN_DEPOSITO',
    empty: 'No hay paquetes en terminales ni sucursales.',
    related: [{ label: 'Gestionar recorridos', to: '/recorridos' }, { label: 'En camino', to: '/monitor/en-camino' }],
  },
  'en-camino': {
    title: 'En camino',
    description: 'En tránsito entre sucursales o en reparto a domicilio. Cada fila indica el repartidor, el día del recorrido y la parada.',
    icon: Truck,
    group: 'EN_CAMINO',
    empty: 'No hay paquetes viajando en este momento.',
    related: [{ label: 'Control de descarga', to: '/terminal/descarga' }, { label: 'Entregados', to: '/monitor/entregados' }],
  },
  'para-retirar': {
    title: 'Para retirar',
    description: 'Ya están en la sucursal elegida por el cliente y se pueden retirar presentando el documento.',
    icon: Store,
    group: 'PARA_RETIRAR',
    empty: 'No hay paquetes esperando retiro.',
    related: [{ label: 'Registrar retiro', to: '/sucursal/retiros' }, { label: 'Entregados', to: '/monitor/entregados' }],
  },
  entregados: {
    title: 'Entregados',
    description: 'Entregados a domicilio o retirados en sucursal. En la trazabilidad se ve quién recibió y su firma.',
    icon: CircleCheckBig,
    group: 'ENTREGADOS',
    empty: 'Todavía no se entregó ningún paquete.',
    related: [{ label: 'Reclamos', to: '/monitor/reclamos' }, { label: 'Todos los paquetes', to: '/monitor/paquetes' }],
  },
  incidencias: {
    title: 'Incidencias',
    description: 'Lo que no salió como estaba previsto: visitas fallidas, paquetes que no aparecieron al descargar, sin recorrido o con reclamos en curso.',
    icon: AlertTriangle,
    group: 'CON_PROBLEMAS',
    tabs: [
      { id: 'CON_PROBLEMAS', label: 'Todas' },
      { id: 'NO_ENTREGADOS', label: 'Visitas fallidas' },
      { id: 'FALTANTES', label: 'Faltantes en la descarga' },
      { id: 'SIN_RECORRIDO', label: 'Sin recorrido' },
      { id: 'CON_RECLAMO', label: 'Con reclamo' },
    ],
    empty: 'No hay incidencias abiertas. Todo en orden.',
    related: [{ label: 'Reclamos', to: '/monitor/reclamos' }, { label: 'Gestionar recorridos', to: '/recorridos' }, { label: 'Control de descarga', to: '/terminal/descarga' }],
  },
}
