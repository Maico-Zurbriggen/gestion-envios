import { AlertTriangle, Boxes } from 'lucide-react'
import type { PackagesSectionConfig } from './pages/MonitorPackagesPage'

/** Subsecciones de listado del monitor, por ruta relativa a `/monitor`. */
export const MONITOR_SECTIONS: Record<string, PackagesSectionConfig> = {
  paquetes: {
    title: 'Paquetes',
    description: 'Todos los paquetes registrados. Elegí una etapa, buscá por paquete, código, persona o destino, y exportá el resultado.',
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
      { id: 'DEVOLUCIONES', label: 'Devoluciones' },
      { id: 'VENCIDOS', label: 'Vencidos' },
    ],
    empty: 'No hay paquetes en esta etapa.',
    related: [
      { label: 'Incidencias', to: '/monitor/incidencias' },
      { label: 'Reclamos', to: '/monitor/reclamos' },
    ],
  },
  incidencias: {
    title: 'Incidencias',
    description: 'Lo que no salió como estaba previsto: visitas fallidas, paquetes que no aparecieron al cargar o descargar, sin recorrido, con reclamos en curso o que vuelven al remitente.',
    icon: AlertTriangle,
    group: 'CON_PROBLEMAS',
    tabs: [
      { id: 'CON_PROBLEMAS', label: 'Todas' },
      { id: 'NO_ENTREGADOS', label: 'Visitas fallidas' },
      { id: 'FALTANTES', label: 'Faltantes en la descarga' },
      { id: 'SIN_RECORRIDO', label: 'Sin recorrido' },
      { id: 'CON_RECLAMO', label: 'Con reclamo' },
      { id: 'DEVOLUCIONES', label: 'Devoluciones' },
    ],
    empty: 'No hay incidencias abiertas. Todo en orden.',
    related: [
      { label: 'Reclamos', to: '/monitor/reclamos' },
      { label: 'Gestionar recorridos', to: '/recorridos' },
      { label: 'Carga y descarga', to: '/terminal/descarga' },
    ],
  },
}

/** Rutas anteriores a la simplificación: llevan a Paquetes con la etapa elegida. */
export const LEGACY_SECTIONS: Record<string, string> = {
  pendientes: 'PENDIENTES',
  deposito: 'EN_DEPOSITO',
  'en-camino': 'EN_CAMINO',
  'para-retirar': 'PARA_RETIRAR',
  entregados: 'ENTREGADOS',
}
