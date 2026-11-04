import { lazy, Suspense, type ComponentType } from 'react'
import { PageLoading } from '../shared/components/PageLoading'

// Páginas que se descargan recién al entrar. Sucursales trae el mapa (Leaflet).
const UsersPage = lazy(() => import('../features/users/pages/UsersPage').then((m) => ({ default: m.UsersPage })))
const PickupPage = lazy(() => import('../features/pickup/pages/PickupPage').then((m) => ({ default: m.PickupPage })))
const BranchesPage = lazy(() => import('../features/shipments/pages/BranchesPage').then((m) => ({ default: m.BranchesPage })))
const ChooseBranchPage = lazy(() => import('../features/auth/pages/ChooseBranchPage').then((m) => ({ default: m.ChooseBranchPage })))
const AdminBranchesPage = lazy(() => import('../features/branches/pages/AdminBranchesPage').then((m) => ({ default: m.AdminBranchesPage })))
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
export const BranchesRoute = () => <OnDemand page={BranchesPage} />
export const FaqRoute = () => <OnDemand page={FaqPage} />
export const ChooseBranchRoute = () => <OnDemand page={ChooseBranchPage} />
export const AdminBranchesRoute = () => <OnDemand page={AdminBranchesPage} />
