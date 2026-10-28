import {
  AlertTriangle,
  ArrowRight,
  BellOff,
  Bike,
  Boxes,
  CalendarClock,
  CircleCheckBig,
  MessageSquareWarning,
  MonitorDot,
  PackagePlus,
  RefreshCw,
  Route,
  ScanBarcode,
  XCircle,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { NAVIGATION_MODULES } from '../../../app/navigation'
import { PageHeader, StatCard } from '../../../shared/components/PageHeader'
import { useMonitorSummary } from '../hooks/useMonitor'
import { countForSection, formatRelative, GROUP_META, percent, PIPELINE } from '../utils/monitorFormat'

const MONITOR = NAVIGATION_MODULES.find((module) => module.id === 'monitor')!
const GROUP_PATHS: Record<string, string> = {
  PENDIENTES: '/monitor/pendientes',
  EN_DEPOSITO: '/monitor/deposito',
  EN_CAMINO: '/monitor/en-camino',
  PARA_RETIRAR: '/monitor/para-retirar',
  ENTREGADOS: '/monitor/entregados',
  NO_ENTREGADOS: '/monitor/incidencias?grupo=NO_ENTREGADOS',
}

export function MonitorOverviewPage() {
  const summaryQuery = useMonitorSummary()
  const summary = summaryQuery.data
  const sections = (MONITOR.children ?? []).filter((child) => child.path !== MONITOR.path)

  const attention = summary
    ? [
        { label: 'Visitas fallidas', detail: 'Paquetes que el repartidor no pudo entregar.', count: summary.byGroup.NO_ENTREGADOS ?? 0, icon: XCircle, to: '/monitor/incidencias?grupo=NO_ENTREGADOS', tone: 'danger' },
        { label: 'Sin recorrido', detail: 'Quedaron fuera de la generación de recorridos.', count: summary.withoutRoute, icon: AlertTriangle, to: '/monitor/incidencias?grupo=SIN_RECORRIDO', tone: 'warning' },
        { label: 'Reclamos en curso', detail: 'Abiertos o en revisión, esperando respuesta.', count: summary.openClaims, icon: MessageSquareWarning, to: '/monitor/reclamos', tone: 'warning' },
        { label: 'Avisos que no llegaron', detail: 'Correos o WhatsApp rechazados. Se reenvían desde Recibir paquetes.', count: summary.failedNotifications, icon: BellOff, to: '/terminal/recepcion', tone: 'danger' },
      ]
    : []

  return (
    <main className="monitor-page">
      <PageHeader
        icon={MonitorDot}
        eyebrow="Monitor de envíos"
        title="Panel general"
        description="El estado de todos los paquetes de un vistazo: en qué etapa están, qué pasó hoy y qué necesita atención."
        actions={
          <button className="btn" type="button" onClick={() => void summaryQuery.refetch()} disabled={summaryQuery.isFetching}>
            <RefreshCw size={17} className={summaryQuery.isFetching ? 'loading-icon' : undefined} aria-hidden="true" />
            {summary ? `Actualizado ${formatRelative(summary.generatedAt)}` : 'Actualizar'}
          </button>
        }
      />

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
        <StatCard label="Visitas fallidas hoy" value={summary?.today.failedVisits ?? '—'} icon={XCircle} tone="muted" hint="Se reintentan en otro recorrido" />
        <StatCard label="Reclamos en curso" value={summary?.openClaims ?? '—'} icon={MessageSquareWarning} tone="info" hint="Abiertos o en revisión" />
      </section>

      <section className="surface-card monitor-flow" aria-labelledby="monitor-flow-title">
        <header className="monitor-card__header">
          <div>
            <h2 id="monitor-flow-title">Flujo de paquetes</h2>
            <p>Cuántos paquetes hay en cada etapa del recorrido, del registro a la entrega.</p>
          </div>
        </header>
        <div className="monitor-flow__bar" aria-hidden="true">
          {PIPELINE.map((group) => {
            const count = summary?.byGroup[group] ?? 0
            return count ? (
              <span
                key={group}
                className={`monitor-flow__segment tone-${GROUP_META[group].tone}`}
                style={{ flexGrow: count }}
                title={`${GROUP_META[group].label}: ${count}`}
              />
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
                <Link className={`monitor-stage tone-${meta.tone}`} to={GROUP_PATHS[group]}>
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

      <div className="monitor-columns">
        <section className="surface-card monitor-card" aria-labelledby="monitor-today-title">
          <header className="monitor-card__header">
            <div>
              <h2 id="monitor-today-title">
                <CalendarClock size={18} aria-hidden="true" />
                Actividad de hoy
              </h2>
              <p>Movimientos registrados desde las 00:00.</p>
            </div>
          </header>
          <dl className="monitor-metrics">
            <div>
              <dt><PackagePlus size={16} aria-hidden="true" />Registrados</dt>
              <dd>{summary?.today.registered ?? '—'}</dd>
            </div>
            <div>
              <dt><ScanBarcode size={16} aria-hidden="true" />Recibidos en terminal</dt>
              <dd>{summary?.today.received ?? '—'}</dd>
            </div>
            <div>
              <dt><CircleCheckBig size={16} aria-hidden="true" />Entregados</dt>
              <dd>{summary?.today.delivered ?? '—'}</dd>
            </div>
            <div>
              <dt><XCircle size={16} aria-hidden="true" />Visitas fallidas</dt>
              <dd>{summary?.today.failedVisits ?? '—'}</dd>
            </div>
          </dl>
        </section>

        <section className="surface-card monitor-card" aria-labelledby="monitor-routes-title">
          <header className="monitor-card__header">
            <div>
              <h2 id="monitor-routes-title">
                <Route size={18} aria-hidden="true" />
                Recorridos de hoy
              </h2>
              <p>Planificación y reparto del día.</p>
            </div>
            <Link className="monitor-link" to="/recorridos">
              Gestionar
              <ArrowRight size={15} aria-hidden="true" />
            </Link>
          </header>
          <dl className="monitor-metrics">
            <div>
              <dt>Generados</dt>
              <dd>{summary?.routesToday.generated ?? '—'}</dd>
            </div>
            <div>
              <dt>En curso</dt>
              <dd>{summary?.routesToday.inProgress ?? '—'}</dd>
            </div>
            <div>
              <dt>Finalizados</dt>
              <dd>{summary?.routesToday.finished ?? '—'}</dd>
            </div>
            <div>
              <dt><Bike size={16} aria-hidden="true" />Repartidores en ruta</dt>
              <dd>{summary?.routesToday.driversOnRoute ?? '—'}</dd>
            </div>
          </dl>
        </section>

        <section className="surface-card monitor-card monitor-card--attention" aria-labelledby="monitor-attention-title">
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
      </div>

      <section aria-labelledby="monitor-sections-title">
        <header className="monitor-section-title">
          <p className="eyebrow">Secciones del monitor</p>
          <h2 id="monitor-sections-title">Elegí qué querés revisar</h2>
        </header>
        <div className="section-card-grid">
          {sections.map((section) => {
            const Icon = section.icon
            const count = countForSection(section.id, summary)
            return (
              <article className="section-card" key={section.id}>
                <div className="section-card__top">
                  <span className="section-card__icon" aria-hidden="true">
                    <Icon size={22} />
                  </span>
                  {count !== undefined ? <span className="section-card__count">{count}</span> : null}
                </div>
                <h3>{section.label}</h3>
                <p>{section.description}</p>
                <Link className="section-card__link" to={section.path}>
                  Abrir {section.label.toLowerCase()}
                  <ArrowRight size={16} aria-hidden="true" />
                </Link>
              </article>
            )
          })}
        </div>
      </section>
    </main>
  )
}
