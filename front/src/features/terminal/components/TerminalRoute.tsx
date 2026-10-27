import { lazy, Suspense } from 'react'
const TerminalPage = lazy(() => import('../pages/TerminalPage').then((module) => ({ default: module.TerminalPage })))
export function TerminalRoute() {
  return <Suspense fallback={<p role="status">Cargando recepción…</p>}><TerminalPage /></Suspense>
}
