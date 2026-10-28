import { lazy, Suspense, type ComponentType } from 'react'
import { PageLoading } from '../shared/components/PageLoading'

// Páginas que se descargan recién al entrar. Sucursales trae el mapa (Leaflet).
const UsersPage = lazy(() => import('../features/users/pages/UsersPage').then((m) => ({ default: m.UsersPage })))
const PickupPage = lazy(() => import('../features/pickup/pages/PickupPage').then((m) => ({ default: m.PickupPage })))
const EmailTemplatesPage = lazy(() => import('../features/emails/pages/EmailTemplatesPage').then((m) => ({ default: m.EmailTemplatesPage })))
const BranchesPage = lazy(() => import('../features/shipments/pages/BranchesPage').then((m) => ({ default: m.BranchesPage })))
const FaqPage = lazy(() => import('../features/faq/pages/FaqPage').then((m) => ({ default: m.FaqPage })))

function OnDemand({ page: Page }: { page: ComponentType }) {
  return (
    <Suspense fallback={<PageLoading label="Cargando…" />}>
      <Page />
    </Suspense>
  )
}

export const UsersRoute = () => <OnDemand page={UsersPage} />
export const PickupRoute = () => <OnDemand page={PickupPage} />
export const EmailTemplatesRoute = () => <OnDemand page={EmailTemplatesPage} />
export const BranchesRoute = () => <OnDemand page={BranchesPage} />
export const FaqRoute = () => <OnDemand page={FaqPage} />
