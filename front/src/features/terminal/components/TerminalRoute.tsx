import { lazy, Suspense } from 'react'
import { PageLoading } from '../../../shared/components/PageLoading'
const TerminalPage = lazy(() => import('../pages/TerminalPage').then((module) => ({ default: module.TerminalPage })))
export function TerminalRoute() {
  return <Suspense fallback={<PageLoading label="Cargando la recepción…" />}><TerminalPage /></Suspense>
}
