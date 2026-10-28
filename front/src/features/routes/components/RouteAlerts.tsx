import { useState } from 'react'
import { BellRing, Check, Copy, RefreshCw } from 'lucide-react'
import { TraceLink } from '../../monitor/components/TraceLink'
import { Link } from 'react-router-dom'
import { useResolveRouteAlert, useRouteAlerts } from '../hooks/useRoutes'
import type { RouteAlert } from '../types/route.types'
import { ConfirmRouteAction } from './ConfirmRouteAction'
import { RouteError, RouteLoading } from './RouteFeedback'

export function RouteAlerts({ branchId, busy }: { branchId: number; busy: boolean }) {
  const query = useRouteAlerts(branchId)
  const mutation = useResolveRouteAlert()
  const [confirmation, setConfirmation] = useState<RouteAlert | null>(null)
  const [notice, setNotice] = useState('')

  async function copy(code: string) {
    try { await navigator.clipboard.writeText(code); setNotice(`Código ${code} copiado.`) }
    catch { setNotice('No pudimos copiar el código. Podés seleccionarlo en la tarjeta.') }
  }

  return <section className="route-panel route-alerts" aria-labelledby="route-alerts-title">
    <div className="route-panel__heading"><BellRing size={22} aria-hidden="true" /><div><h2 id="route-alerts-title">Paquetes sin recorrido{query.data ? ` (${query.data.length})` : ''}</h2><p>Alertas pendientes de {branchId ? 'la sucursal seleccionada' : 'todas las sucursales'}, para ambos tipos de reparto. No dependen de la fecha del filtro.</p></div><button className="route-button" type="button" disabled={busy || query.isFetching} onClick={() => void query.refetch()}><RefreshCw size={17} className={query.isFetching ? 'loading-icon' : undefined} aria-hidden="true" /> Actualizar alertas</button></div>
    {query.isPending && <RouteLoading label="Consultando paquetes sin recorrido…" />}
    {query.isError && <RouteError error={query.error} onRetry={() => void query.refetch()} pending={query.isFetching} />}
    {mutation.isError && <RouteError error={mutation.error} />}
    {notice && <p className="route-hint" role="status">{notice}</p>}
    {query.data?.length === 0 && <p className="route-empty" role="status"><Check size={21} aria-hidden="true" /> No hay alertas pendientes en esta consulta.</p>}
    {query.data && query.data.length > 0 && <ul className="route-alerts__list">{query.data.map((alert) => <li key={alert.id}>
      <div><strong>{alert.packageNumber}</strong><p>{alert.destination}</p><p className="route-alerts__reason">{alert.description}</p><TraceLink code={alert.packageNumber} className="route-alerts__trace" /></div>
      <div className="route-actions"><button className="route-button" type="button" onClick={() => void copy(alert.packageNumber)}><Copy size={16} aria-hidden="true" /> Copiar código</button><Link className="route-button" to={`/seguimiento?token=${encodeURIComponent(alert.trackingToken)}`} target="_blank" rel="noopener noreferrer">Ver seguimiento</Link><button className="route-button" type="button" disabled={busy} onClick={() => setConfirmation(alert)}><Check size={16} aria-hidden="true" /> Marcar atendida</button></div>
    </li>)}</ul>}
    {confirmation && <ConfirmRouteAction title="¿Marcar esta alerta como atendida?" description={`Paquete ${confirmation.packageNumber}. Usá esta opción si el problema se atendió por fuera del sistema. Si sigue sin recorrido, el próximo control volverá a alertarlo.`} confirmLabel="Marcar atendida" pending={busy} onCancel={() => setConfirmation(null)} onConfirm={() => mutation.mutate(confirmation.id, { onSuccess: () => { setNotice('Alerta marcada como atendida.'); setConfirmation(null) }, onError: () => setConfirmation(null) })} />}
  </section>
}
