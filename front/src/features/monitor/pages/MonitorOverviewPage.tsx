import {
  AlertTriangle,
  ArrowRight,
  BellOff,
  Bike,
  Boxes,
  CalendarClock,
  CircleCheckBig,
  ClipboardCheck,
  MessageSquareWarning,
  MonitorDot,
  PackagePlus,
  RefreshCw,
  Route,
  ScanBarcode,
  TimerReset,
  TimerOff,
  Undo2,
  XCircle,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { PageHeader, StatCard } from '../../../shared/components/PageHeader'
import { PackageSearchBar } from '../components/PackageSearchBar'
import { showToast } from '../../../shared/services/toast'
import { useMonitorSummary, useProcessDeadlines } from '../hooks/useMonitor'
import { formatRelative, GROUP_META, percent, PIPELINE } from '../utils/monitorFormat'

/** Cada etapa del flujo abre el listado ya filtrado. */
function stagePath(group: string) {
  return group === 'NO_ENTREGADOS' ? '/monitor/incidencias?grupo=NO_ENTREGADOS' : `/monitor/paquetes?grupo=${group}`
}

export function MonitorOverviewPage() {
  const summaryQuery = useMonitorSummary()
  const summary = summaryQuery.data
  const deadlines = useProcessDeadlines()

  function reviewDeadlines() {
    deadlines.mutate(undefined, {
      onSuccess: ({ result }) => {
        const parts = [
          result.expiredRegistrations ? `${result.expiredRegistrations} ${result.expiredRegistrations === 1 ? 'registro vencido' : 'registros vencidos'}` : null,
          result.returnsStarted ? `${result.returnsStarted} ${result.returnsStarted === 1 ? 'devolución iniciada' : 'devoluciones iniciadas'}` : null,
        ].filter(Boolean)
        showToast(parts.length ? `Plazos revisados: ${parts.join(' y ')}. Se avisó a los clientes.` : 'Plazos revisados: no había nada vencido.')
      },
      onError: (error) => showToast(error.message, 'error'),
    })
  }

  const attention = summary
    ? [
        { label: 'Visitas fallidas', detail: 'El repartidor no pudo entregar.', count: summary.byGroup.NO_ENTREGADOS ?? 0, icon: XCircle, to: '/monitor/incidencias?grupo=NO_ENTREGADOS', tone: 'danger' },
        { label: 'Faltantes en la descarga', detail: 'No aparecieron al descargar en destino.', count: summary.missing, icon: ClipboardCheck, to: '/monitor/incidencias?grupo=FALTANTES', tone: 'danger' },
        { label: 'Devoluciones', detail: 'No se retiraron a tiempo: vuelven al remitente.', count: summary.byGroup.DEVOLUCIONES ?? 0, icon: Undo2, to: '/monitor/paquetes?grupo=DEVOLUCIONES', tone: 'warning' },
        { label: 'Sin recorrido', detail: 'Quedaron fuera de los recorridos generados.', count: summary.withoutRoute, icon: AlertTriangle, to: '/monitor/incidencias?grupo=SIN_RECORRIDO', tone: 'warning' },
        { label: 'Reclamos en curso', detail: 'Abiertos o en revisión.', count: summary.openClaims, icon: MessageSquareWarning, to: '/monitor/reclamos', tone: 'warning' },
        { label: 'Avisos que no llegaron', detail: 'Se reenvían desde Recibir paquetes.', count: summary.failedNotifications, icon: BellOff, to: '/terminal/recepcion', tone: 'danger' },
        { label: 'Registros vencidos', detail: 'No se llevaron a la sucursal en 10 días.', count: summary.byGroup.VENCIDOS ?? 0, icon: TimerOff, to: '/monitor/paquetes?grupo=VENCIDOS', tone: 'neutral' },
      ]
    : []

  const today = summary
    ? [
        { label: 'Registrados', value: summary.today.registered, icon: PackagePlus },
        { label: 'Recibidos en terminal', value: summary.today.received, icon: ScanBarcode },
        { label: 'Entregados', value: summary.today.delivered, icon: CircleCheckBig },
        { label: 'Visitas fallidas', value: summary.today.failedVisits, icon: XCircle },
        { label: 'Recorridos en curso', value: `${summary.routesToday.inProgress} de ${summary.routesToday.total}`, icon: Route },
        { label: 'Repartidores en ruta', value: summary.routesToday.driversOnRoute, icon: Bike },
      ]
    : []

  return (
    <main className="monitor-page">
      <PageHeader
        icon={MonitorDot}
        title="Monitor de envíos"
        description="El estado de todos los paquetes de un vistazo: en qué etapa están, qué necesita atención y qué pasó hoy."
        actions={
          <>
            <button
              className="btn btn--ghost"
              type="button"
              onClick={reviewDeadlines}
              disabled={deadlines.isPending}
              title="Vence los registros sin admitir y devuelve lo que no se retiró a tiempo. También se hace solo cada 30 minutos."
            >
              <TimerReset size={17} className={deadlines.isPending ? 'loading-icon' : undefined} aria-hidden="true" />
              {deadlines.isPending ? 'Revisando…' : 'Revisar plazos ahora'}
            </button>
            <button className="btn" type="button" onClick={() => void summaryQuery.refetch()} disabled={summaryQuery.isFetching}>
              <RefreshCw size={17} className={summaryQuery.isFetching ? 'loading-icon' : undefined} aria-hidden="true" />
              {summary ? `Actualizado ${formatRelative(summary.generatedAt)}` : 'Actualizar'}
            </button>
          </>
        }
      />

      <section className="surface-card trace-start trace-start--compact" aria-label="Ir a un paquete">
        <PackageSearchBar />
      </section>

      {summaryQuery.isError ? (
        <div className="list-card list-empty" role="alert">
          <AlertTriangle size={30} aria-hidden="true" />
          <strong>No pudimos cargar el monitor</strong>
          <p>{summaryQuery.error.message}</p>
        </div>
      ) : null}

      <section className="stat-grid" aria-label="Indicadores generales">
        <StatCard label="Paquetes" value={summary?.totalPackages ?? '—'} icon={Boxes} hint={summary ? `${summary.totalShipments} envíos registrados` : undefined} />
        <StatCard label="Entregados hoy" value={summary?.today.delivered ?? '—'} icon={CircleCheckBig} tone="success" hint="A domicilio o en sucursal" />
        <StatCard label="Incidencias" value={summary?.withProblems ?? '—'} icon={AlertTriangle} tone="muted" hint="Fallidas, faltantes, sin recorrido o con reclamo" />
        <StatCard label="Reclamos en curso" value={summary?.openClaims ?? '—'} icon={MessageSquareWarning} tone="info" hint="Abiertos o en revisión" />
      </section>

      <section className="surface-card monitor-flow" aria-labelledby="monitor-flow-title">
        <header className="monitor-card__header">
          <div>
            <h2 id="monitor-flow-title">Paquetes por etapa</h2>
            <p>Del registro a la entrega. Tocá una etapa para ver sus paquetes.</p>
          </div>
          <Link className="monitor-link" to="/monitor/paquetes">
            Ver todos
            <ArrowRight size={15} aria-hidden="true" />
          </Link>
        </header>
        <div className="monitor-flow__bar" aria-hidden="true">
          {PIPELINE.map((group) => {
            const count = summary?.byGroup[group] ?? 0
            return count ? (
              <span key={group} className={`monitor-flow__segment tone-${GROUP_META[group].tone}`} style={{ flexGrow: count }} />
            ) : null
          })}
        </div>
        <ol className="monitor-flow__stages">
          {PIPELINE.map((group) => {
            const meta = GROUP_META[group]
            const Icon = meta.icon
            const count = summary?.byGroup[group] ?? 0
            return (
              <li key={group}>
                <Link className={`monitor-stage tone-${meta.tone}`} to={stagePath(group)}>
                  <span className="monitor-stage__icon" aria-hidden="true">
                    <Icon size={18} />
                  </span>
                  <span className="monitor-stage__text">
                    <small>{meta.label}</small>
                    <strong>{summary ? count : '—'}</strong>
                    <span>{summary ? `${percent(count, summary.totalPackages)} % del total` : ' '}</span>
                  </span>
                </Link>
              </li>
            )
          })}
        </ol>
      </section>

      <div className="monitor-columns monitor-columns--two">
        <section className="surface-card monitor-card" aria-labelledby="monitor-attention-title">
          <header className="monitor-card__header">
            <div>
              <h2 id="monitor-attention-title">
                <AlertTriangle size={18} aria-hidden="true" />
                Requieren atención
              </h2>
              <p>Lo que conviene resolver primero.</p>
            </div>
          </header>
          <ul className="monitor-attention">
            {attention.map((item) => {
              const Icon = item.icon
              return (
                <li key={item.label}>
                  <Link to={item.to} className={`monitor-attention__item ${item.count ? `tone-${item.tone}` : 'is-clear'}`}>
                    <Icon size={18} aria-hidden="true" />
                    <span>
                      <strong>{item.label}</strong>
                      <small>{item.count ? item.detail : 'Sin pendientes.'}</small>
                    </span>
                    <span className="monitor-attention__count">{item.count}</span>
                  </Link>
                </li>
              )
            })}
          </ul>
        </section>

        <section className="surface-card monitor-card" aria-labelledby="monitor-today-title">
          <header className="monitor-card__header">
            <div>
              <h2 id="monitor-today-title">
                <CalendarClock size={18} aria-hidden="true" />
                Hoy
              </h2>
              <p>Movimientos y recorridos desde las 00:00.</p>
            </div>
            <Link className="monitor-link" to="/recorridos">
              Recorridos
              <ArrowRight size={15} aria-hidden="true" />
            </Link>
          </header>
          <dl className="monitor-metrics">
            {today.map((item) => {
              const Icon = item.icon
              return (
                <div key={item.label}>
                  <dt>
                    <Icon size={16} aria-hidden="true" />
                    {item.label}
                  </dt>
                  <dd>{item.value}</dd>
                </div>
              )
            })}
          </dl>
        </section>
      </div>
    </main>
  )
}
