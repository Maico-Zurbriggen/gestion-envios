import type { RouteObject } from 'react-router-dom'
import {
  ClaimsAdminRoute,
  MonitorOverviewRoute,
  MonitorPackagesRoute,
  MonitorShellRoute,
  PackageTraceRoute,
} from './components/MonitorLazy'
import { MONITOR_SECTIONS } from './monitorSections'

/** Sección general «Monitor» con sus subsecciones. */
export const monitorRoute: RouteObject = {
  path: '/monitor',
  element: <MonitorShellRoute />,
  children: [
    { index: true, element: <MonitorOverviewRoute /> },
    ...Object.entries(MONITOR_SECTIONS).map(([path, config]) => ({
      path,
      element: <MonitorPackagesRoute key={path} config={config} />,
    })),
    { path: 'reclamos', element: <ClaimsAdminRoute /> },
    { path: 'trazabilidad', element: <PackageTraceRoute /> },
    { path: 'trazabilidad/:code', element: <PackageTraceRoute /> },
  ],
}
