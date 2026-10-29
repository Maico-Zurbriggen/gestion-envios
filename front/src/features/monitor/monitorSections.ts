import { Boxes } from 'lucide-react'
import type { PackagesSectionConfig } from './pages/MonitorPackagesPage'

/** Subsecciones de listado del monitor, por ruta relativa a `/monitor`. */
export const MONITOR_SECTIONS: Record<string, PackagesSectionConfig> = {
  paquetes: {
    title: 'Paquetes',
    description: 'Todos los paquetes registrados. Elegí una etapa y buscá por paquete, código, persona o destino.',
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
      { label: 'Recorridos', to: '/recorridos' },
      { label: 'Reclamos', to: '/monitor/reclamos' },
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
