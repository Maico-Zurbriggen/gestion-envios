import { lazy, Suspense, type ReactNode } from 'react'
import { LoaderCircle } from 'lucide-react'
import type { PackagesSectionConfig } from '../pages/MonitorPackagesPage'

// El monitor se carga recién al entrar: el mapa y la impresión pesan.
const MonitorLayout = lazy(() => import('./MonitorLayout').then((m) => ({ default: m.MonitorLayout })))
const MonitorOverviewPage = lazy(() => import('../pages/MonitorOverviewPage').then((m) => ({ default: m.MonitorOverviewPage })))
const MonitorPackagesPage = lazy(() => import('../pages/MonitorPackagesPage').then((m) => ({ default: m.MonitorPackagesPage })))
const PackageTracePage = lazy(() => import('../pages/PackageTracePage').then((m) => ({ default: m.PackageTracePage })))
const ClaimsAdminPage = lazy(() => import('../pages/ClaimsAdminPage').then((m) => ({ default: m.ClaimsAdminPage })))

function Loading({ children }: { children: ReactNode }) {
  return (
    <Suspense
      fallback={
        <p className="monitor-loading" role="status">
          <LoaderCircle className="loading-icon" size={20} aria-hidden="true" />
          Cargando el monitor…
        </p>
      }
    >
      {children}
    </Suspense>
  )
}

export function MonitorShellRoute() {
  return <Loading><MonitorLayout /></Loading>
}

export function MonitorOverviewRoute() {
  return <Loading><MonitorOverviewPage /></Loading>
}

export function MonitorPackagesRoute({ config }: { config: PackagesSectionConfig }) {
  return <Loading><MonitorPackagesPage config={config} /></Loading>
}

export function PackageTraceRoute() {
  return <Loading><PackageTracePage /></Loading>
}

export function ClaimsAdminRoute() {
  return <Loading><ClaimsAdminPage /></Loading>
}
