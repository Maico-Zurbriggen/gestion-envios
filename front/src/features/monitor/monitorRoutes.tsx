import { Navigate, type RouteObject } from 'react-router-dom'
import {
  ClaimsAdminRoute,
  MonitorPackagesRoute,
  MonitorShellRoute,
  PackageTraceRoute,
} from './components/MonitorLazy'
import { LEGACY_SECTIONS, MONITOR_SECTIONS } from './monitorSections'

/** Sección general «Monitor»: Paquetes por etapa, Reclamos y la trazabilidad de cada paquete. */
export const monitorRoute: RouteObject = {
  path: '/monitor',
  element: <MonitorShellRoute />,
  children: [
    { index: true, element: <Navigate to="/monitor/paquetes" replace /> },
    ...Object.entries(MONITOR_SECTIONS).map(([path, config]) => ({
      path,
      element: <MonitorPackagesRoute key={path} config={config} />,
    })),
    ...Object.entries(LEGACY_SECTIONS).map(([path, group]) => ({
      path,
      element: <Navigate to={`/monitor/paquetes?grupo=${group}`} replace />,
    })),
    { path: 'reclamos', element: <ClaimsAdminRoute /> },
    { path: 'trazabilidad', element: <PackageTraceRoute /> },
    { path: 'trazabilidad/:code', element: <PackageTraceRoute /> },
  ],
}
