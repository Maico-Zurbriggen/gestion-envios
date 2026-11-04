import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  CalendarDays, CheckCircle2, ChevronLeft, ChevronRight, Cpu, Inbox, LoaderCircle, Package, Plus, RefreshCw, Route, ScanBarcode, Truck, WandSparkles, XCircle,
} from 'lucide-react'
import { useAppSelector } from '../../../app/store'
import { PageHeader } from '../../../shared/components/PageHeader'
import { selectCurrentUser } from '../../auth/redux/authSlice'
import { ActiveBranchNote } from '../../auth/components/ActiveBranchNote'
import { useActiveBranch } from '../../auth/hooks/useActiveBranch'
import { useBranches } from '../../shipments/hooks/useBranches'
import { AutoPlanModal } from '../components/AutoPlanModal'
import { DriverProfilesButton } from '../components/DriverProfiles'
import { NewRouteModal } from '../components/NewRouteModal'
import { RouteError, RouteLoading } from '../components/RouteFeedback'
import { RouteWorkspace } from '../components/RouteWorkspace'
import { useDrivers, usePendingPackages, useRouteCommand, useRoutes, useRoutesBusy, useWaitingSummary } from '../hooks/useRoutes'
import { showToast } from '../../../shared/services/toast'
import {
  dayParts, formatRouteDistance, formatRouteDuration, isRouteEditable, localToday, routeStatusLabels, routeStatusTone, shiftDay, weekOf,
} from '../routePresentation'
import type { DeliveryRouteSummary, DistanceType, WaitingSummary } from '../types/route.types'
import '../routes.css'
import './DeliveryRoutesPage.css'

const DAY_RE = /^\d{4}-\d{2}-\d{2}$/

export function DeliveryRoutesPage() {
  const [params, setParams] = useSearchParams()
  const today = localToday()
  const date = DAY_RE.test(params.get('fecha') ?? '') ? params.get('fecha')! : today
  const selectedId = params.get('recorrido') ?? ''
  const [modal, setModal] = useState<'new' | 'auto' | null>(null)

  // Los recorridos se arman en la sucursal en la que se está trabajando (se cambia arriba).
  const { branch: activeBranch, branches: allowedBranches, choose } = useActiveBranch()
  const branchId = activeBranch?.id ?? 0
  const waiting = useWaitingSummary()
  const here = waiting.data?.branches.find((item) => item.id === branchId)
  const typeParam = params.get('tipo')
  const distanceType: DistanceType = typeParam ? (typeParam === 'larga' ? 'LARGA' : 'CORTA') : here && !here.home && here.between ? 'LARGA' : 'CORTA'
  const week = useMemo(() => weekOf(date), [date])
  const catalog = useBranches()
  // Para la sucursal base de los repartidores, solo las que tiene habilitadas.
  const allowedIds = new Set(allowedBranches.map((item) => item.id))
  const branches = catalog.data?.filter((item) => allowedIds.has(item.id)) ?? []
  const drivers = useDrivers()
  const routes = useRoutes({ branchId, distanceType, from: week[0], to: week[6] })
  const pending = usePendingPackages(branchId, distanceType)
  const busy = useRoutesBusy()
  const user = useAppSelector(selectCurrentUser)
  const branchName = activeBranch?.name ?? ''

  const dayRoutes = useMemo(() => (routes.data ?? []).filter((route) => route.date === date)
    .sort((a, b) => order(a) - order(b) || a.driver.name.localeCompare(b.driver.name)), [routes.data, date])
  // Repartidores aptos para esta sucursal y tipo, y los que ya tienen recorrido activo ese día.
  const eligible = (drivers.data ?? []).filter((driver) => driver.available && driver.branch?.id === branchId && driver.distanceType === distanceType)
  const busyDriverIds = new Set(dayRoutes.filter((route) => route.status !== 'FINALIZADO').map((route) => route.driver.id))

  /** Cambia la URL: el día, el tipo y el recorrido abierto se pueden compartir y el botón Atrás vuelve. */
  function go(next: { fecha?: string; tipo?: DistanceType; recorrido?: string | null }, replace = false) {
    setParams((current) => {
      const url = new URLSearchParams(current)
      if (next.fecha) url.set('fecha', next.fecha)
      if (next.tipo) url.set('tipo', next.tipo === 'LARGA' ? 'larga' : 'corta')
      if (next.recorrido !== undefined) {
        if (next.recorrido) url.set('recorrido', next.recorrido)
        else url.delete('recorrido')
      }
      return url
    }, { replace })
  }

  function setBranchId(value: number) {
    choose(value)
  }

  if (selectedId) {
    const open = routes.data?.find((route) => route.id === selectedId)
    const forRoute = (drivers.data ?? []).filter((driver) => driver.available
      && (!open || (driver.branch?.id === open.branchId && driver.distanceType === open.distanceType)))
    return <main className="routes-page">
      <RouteWorkspace key={selectedId} id={selectedId} drivers={forRoute} busyDriverIds={busyDriverIds}
        onBack={() => go({ recorrido: null })} onDeleted={() => go({ recorrido: null }, true)} />
    </main>
  }

  const needsBranch = !branchId
  const planTitle = needsBranch ? 'Elegí una sucursal para armar recorridos' : undefined

  return <main className="routes-page">
    <PageHeader icon={Route} title="Recorridos"
      description="Armá el reparto del día: cada recorrido es un repartidor con sus paquetes en orden de visita."
      actions={<>
        <DriverProfilesButton drivers={drivers.data ?? []} branches={branches} busy={busy} canCreateUser={user?.role === 'SUPERADMIN'} />
        <button className="btn btn--ghost" type="button" onClick={() => setModal('auto')} disabled={needsBranch} title={planTitle}><Cpu size={17} aria-hidden="true" /> Armar automáticamente</button>
        <button className="btn btn--primary" type="button" onClick={() => setModal('new')} disabled={needsBranch} title={planTitle}><Plus size={17} aria-hidden="true" /> Nuevo recorrido</button>
      </>} />

    <Flow waiting={waiting.data} branchId={branchId} distanceType={distanceType} dayPackages={dayRoutes.reduce((sum, route) => sum + route.packageCount, 0)}
      onPick={(id, type) => { setBranchId(id); go({ tipo: type }, true) }} />

    <section className="surface-card routes-toolbar" aria-label="Qué recorridos ver">
      <div className="routes-toolbar__row">
        <ActiveBranchNote action="Recorridos que salen de" />
        <div className="segmented routes-toolbar__type" role="group" aria-label="Tipo de reparto">
          <button type="button" aria-pressed={distanceType === 'CORTA'} onClick={() => go({ tipo: 'CORTA' }, true)}><Truck size={15} aria-hidden="true" /> A domicilio</button>
          <button type="button" aria-pressed={distanceType === 'LARGA'} onClick={() => go({ tipo: 'LARGA' }, true)}><Route size={15} aria-hidden="true" /> Entre sucursales</button>
        </div>
        <span className="routes-toolbar__spacer" />
        <button className="icon-action" type="button" onClick={() => void routes.refetch()} disabled={routes.isFetching} aria-label="Actualizar" title="Actualizar">
          <RefreshCw size={16} className={routes.isFetching ? 'loading-icon' : undefined} aria-hidden="true" />
        </button>
      </div>
      <WeekStrip week={week} date={date} today={today} routes={routes.data} onDay={(day) => go({ fecha: day }, true)} />
      <p className="routes-week__help">Elegí el día en que salen los recorridos. Los paquetes en espera no tienen fecha: se suman al recorrido del día que elijas.</p>
    </section>

    {catalog.isError && <RouteError error={catalog.error} onRetry={() => void catalog.refetch()} pending={catalog.isFetching} />}
    {routes.isError && <RouteError error={routes.error} onRetry={() => void routes.refetch()} pending={routes.isFetching} />}

    <DayStats routes={dayRoutes} loading={routes.isPending} />

    {!needsBranch && (pending.data?.length ?? 0) > 0 && <div className="routes-waiting" role="status">
      <Inbox size={20} aria-hidden="true" />
      <p><strong>{pending.data!.length} {pending.data!.length === 1 ? 'paquete espera' : 'paquetes esperan'} recorrido</strong> en {branchName}.
        {pending.data!.some((item) => item.issue) && ' Algunos necesitan atención (por ejemplo, ubicar el domicilio).'}</p>
      <button className="route-button" type="button" onClick={() => setModal('auto')}><Cpu size={16} aria-hidden="true" /> Armar automáticamente</button>
      <button className="route-button" type="button" onClick={() => setModal('new')}><Plus size={16} aria-hidden="true" /> Nuevo recorrido</button>
    </div>}

    <section aria-labelledby="routes-day-title" className="routes-day">
      <h2 id="routes-day-title" className="routes-day__title"><span>Recorridos del {dayParts(date).long}</span>{date === today && <span className="badge badge--info">Hoy</span>}</h2>
      {routes.isPending
        ? <RouteLoading label="Cargando recorridos…" />
        : dayRoutes.length === 0
          ? <div className="surface-card routes-empty">
            <Truck size={30} aria-hidden="true" />
            <strong>{date < today ? 'No hubo recorridos este día' : 'Todavía no hay recorridos para este día'}</strong>
            <p>{needsBranch ? 'Elegí una sucursal para armar los recorridos.' : 'Creá uno a mano eligiendo repartidor y paquetes, o dejá que se armen solos con los repartidores libres.'}</p>
            {!needsBranch && date >= today && <div className="route-actions">
              <button className="btn btn--primary" type="button" onClick={() => setModal('new')}><Plus size={17} aria-hidden="true" /> Nuevo recorrido</button>
              <button className="btn btn--ghost" type="button" onClick={() => setModal('auto')}><Cpu size={17} aria-hidden="true" /> Armar automáticamente</button>
            </div>}
            {date !== today && <button className="btn btn--ghost" type="button" onClick={() => go({ fecha: today }, true)}><CalendarDays size={17} aria-hidden="true" /> Ir a hoy</button>}
          </div>
          : <ul className="routes-grid">{dayRoutes.map((route) => <li key={route.id}><RouteCard route={route} onOpen={() => go({ recorrido: route.id })} /></li>)}</ul>}
    </section>

    {modal === 'new' && <NewRouteModal branchId={branchId} branchName={branchName} date={date} distanceType={distanceType} drivers={eligible}
      busyDriverIds={busyDriverIds} onClose={() => setModal(null)} onCreated={(id, day) => { setModal(null); go({ fecha: day, recorrido: id }) }} />}
    {modal === 'auto' && <AutoPlanModal branchId={branchId} branchName={branchName} date={date} distanceType={distanceType} drivers={eligible}
      busyDriverIds={busyDriverIds} onClose={() => setModal(null)} onDone={() => setModal(null)} />}
  </main>
}

/** El circuito en tres pasos, con números reales: así se entiende de dónde salen los paquetes que se arman. */
function Flow({ waiting, branchId, distanceType, dayPackages, onPick }: {
  waiting: WaitingSummary | undefined
  branchId: number
  distanceType: DistanceType
  dayPackages: number
  onPick: (branchId: number, type: DistanceType) => void
}) {
  const withPackages = waiting?.branches.filter((branch) => branch.home + branch.between > 0) ?? []
  const totalWaiting = waiting && withPackages.reduce((sum, branch) => sum + branch.home + branch.between, 0)
  // Los que todavía no llegaron se cuentan en la sucursal donde el cliente dijo que los iba a llevar.
  const notArrived = waiting ? waiting.branches.find((branch) => branch.id === branchId)?.notArrived ?? 0 : undefined
  return <ol className="routes-flow" aria-label="Cómo llegan los paquetes a un recorrido">
    <li className="surface-card">
      <span className="routes-flow__head">Registrados, sin llegar</span>
      <span className="routes-flow__value">{notArrived ?? '…'}</span>
      <p>El cliente registró el envío para traerlo a esta sucursal y todavía no lo llevó. Cuando llega, se recibe acá.</p>
      <Link className="route-button" to="/terminal/recepcion"><ScanBarcode size={16} aria-hidden="true" /> Recibir paquetes</Link>
    </li>
    <li className="surface-card">
      <span className="routes-flow__head">En sucursal, esperan recorrido</span>
      <span className="routes-flow__value">{totalWaiting ?? '…'}</span>
      {waiting && withPackages.length === 0 && <p>Ninguno: todo lo recibido ya tiene recorrido.</p>}
      {waiting && withPackages.length > 0 && <div className="routes-flow__branches">
        {withPackages.map((branch) => {
          const type: DistanceType = branch.home || !branch.between ? 'CORTA' : 'LARGA'
          return <button key={branch.id} type="button" className={`routes-flow__branch${branch.id === branchId ? ' is-active' : ''}`} onClick={() => onPick(branch.id, type)}>
            <strong>{branch.name}</strong>
            <small>{[branch.home && `${branch.home} a domicilio`, branch.between && `${branch.between} entre sucursales`].filter(Boolean).join(' · ')}</small>
          </button>
        })}
      </div>}
    </li>
    <li className="surface-card">
      <span className="routes-flow__head">En recorrido este día</span>
      <span className="routes-flow__value">{dayPackages}</span>
      <p>{distanceType === 'CORTA' ? 'A domicilio' : 'Entre sucursales'}: los paquetes que ya tienen repartidor y orden de visita.</p>
    </li>
  </ol>
}

/** Primero lo que está en la calle, después lo que falta salir y al final lo cerrado. */
function order(route: DeliveryRouteSummary) {
  return route.status === 'EN_CURSO' ? 0 : isRouteEditable(route.status) ? 1 : 2
}

function WeekStrip({ week, date, today, routes, onDay }: {
  week: string[]; date: string; today: string; routes: DeliveryRouteSummary[] | undefined; onDay: (day: string) => void
}) {
  const first = dayParts(week[0])
  const last = dayParts(week[6])
  return <div className="routes-week">
    <div className="routes-week__nav">
      <button className="icon-action" type="button" onClick={() => onDay(shiftDay(date, -7))} aria-label="Semana anterior" title="Semana anterior"><ChevronLeft size={17} aria-hidden="true" /></button>
      <button className="icon-action" type="button" onClick={() => onDay(shiftDay(date, 7))} aria-label="Semana siguiente" title="Semana siguiente"><ChevronRight size={17} aria-hidden="true" /></button>
      <strong>Semana del {first.number} al {last.long.split(' ').slice(1).join(' ')}</strong>
      <span className="routes-toolbar__spacer" />
      {date !== today && <button className="btn btn--ghost" type="button" onClick={() => onDay(today)}><CalendarDays size={16} aria-hidden="true" /> Hoy</button>}
      <input className="form-control routes-week__picker" type="date" value={date} onChange={(event) => event.target.value && onDay(event.target.value)} aria-label="Elegir fecha" />
    </div>
    <div className="routes-week__days" role="tablist" aria-label="Días de la semana">
      {week.map((day) => {
        const parts = dayParts(day)
        const list = routes?.filter((route) => route.date === day) ?? []
        const packages = list.reduce((sum, route) => sum + route.packageCount, 0)
        const delivered = list.reduce((sum, route) => sum + route.delivered, 0)
        return <button key={day} type="button" role="tab" aria-selected={day === date} onClick={() => onDay(day)}
          className={`routes-day-tab${day === date ? ' is-active' : ''}${day === today ? ' is-today' : ''}${day < today ? ' is-past' : ''}`}
          aria-label={`${parts.long}: ${list.length} ${list.length === 1 ? 'recorrido' : 'recorridos'}`}>
          <span className="routes-day-tab__weekday">{parts.weekday}{day === today && <em>hoy</em>}</span>
          <span className="routes-day-tab__number">{parts.number}</span>
          <span className="routes-day-tab__count">{routes === undefined ? ' ' : list.length ? `${list.length} rec. · ${packages} paq.` : 'Sin recorridos'}</span>
          {packages > 0 && <span className="routes-progress" aria-hidden="true"><span style={{ width: `${(delivered / packages) * 100}%` }} /></span>}
        </button>
      })}
    </div>
  </div>
}

function DayStats({ routes, loading }: { routes: DeliveryRouteSummary[]; loading: boolean }) {
  const packages = routes.reduce((sum, route) => sum + route.packageCount, 0)
  const delivered = routes.reduce((sum, route) => sum + route.delivered, 0)
  const failed = routes.reduce((sum, route) => sum + route.failed, 0)
  const onStreet = routes.filter((route) => route.status === 'EN_CURSO').length
  const toLeave = routes.filter((route) => isRouteEditable(route.status)).length
  const tiles = [
    { label: 'Recorridos', value: routes.length, hint: routes.length ? [onStreet && `${onStreet} en reparto`, toLeave && `${toLeave} sin salir`].filter(Boolean).join(' · ') || 'Todos finalizados' : 'Ninguno', icon: Truck },
    { label: 'Paquetes', value: packages, hint: `${packages - delivered - failed} pendientes`, icon: Package },
    { label: 'Entregados', value: delivered, hint: packages ? `${Math.round((delivered / packages) * 100)} % del día` : 'Sin paquetes', icon: CheckCircle2 },
    { label: 'Sin entregar', value: failed, hint: failed ? 'Vuelven a la sucursal' : 'Ninguno', icon: XCircle },
  ]
  return <dl className="routes-stats">
    {tiles.map((tile) => <div key={tile.label} className="surface-card">
      <dt><tile.icon size={15} aria-hidden="true" />{tile.label}</dt>
      <dd>{loading ? '…' : tile.value}</dd>
      <small>{loading ? ' ' : tile.hint}</small>
    </div>)}
  </dl>
}

function RouteCard({ route, onOpen }: { route: DeliveryRouteSummary; onOpen: () => void }) {
  const pending = route.packageCount - route.delivered - route.failed
  const parts = route.driver.name.trim().split(/\s+/)
  const initials = ((parts[0]?.[0] ?? '') + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase()
  return <article className={`surface-card route-card${route.status === 'EN_CURSO' ? ' is-live' : ''}`}>
    <header className="route-card__head">
      <span className="route-avatar" aria-hidden="true">{initials}</span>
      <div>
        <h3><button type="button" className="route-card__open" onClick={onOpen}>{route.driver.name}</button></h3>
        <small>{route.branchName}</small>
      </div>
      <span className={`badge ${routeStatusTone[route.status]}`}>{routeStatusLabels[route.status]}</span>
    </header>
    <dl className="route-card__numbers">
      <div><dt>Paquetes</dt><dd>{route.packageCount}</dd></div>
      <div><dt>Paradas</dt><dd>{route.stopCount}</dd></div>
      <div><dt>Distancia</dt><dd>{route.distanceKm == null ? '—' : formatRouteDistance(route.distanceKm)}</dd></div>
    </dl>
    {route.packageCount > 0 && <>
      <span className="routes-progress routes-progress--card" aria-hidden="true">
        <span style={{ width: `${(route.delivered / route.packageCount) * 100}%` }} />
        <span className="is-failed" style={{ width: `${(route.failed / route.packageCount) * 100}%` }} />
      </span>
      <p className="route-card__progress">
        <span className="is-ok">{route.delivered} entregados</span>
        {route.failed > 0 && <span className="is-failed"> · {route.failed} sin entregar</span>}
        <span> · {pending} pendientes</span>
      </p>
    </>}
    <footer className="route-card__foot">
      <small>{route.durationMinutes == null ? '' : `≈ ${formatRouteDuration(route.durationMinutes)} de manejo`}</small>
      <span className="route-card__actions">
        {(isRouteEditable(route.status) || route.status === 'EN_CURSO') && <OptimizeRouteButton route={route} />}
        <button className="route-button" type="button" onClick={onOpen}>{isRouteEditable(route.status) ? 'Armar' : 'Ver'}</button>
      </span>
    </footer>
  </article>
}

/** Ordena las paradas por el camino más rápido por calles, desde la tarjeta del día. */
function OptimizeRouteButton({ route }: { route: DeliveryRouteSummary }) {
  const command = useRouteCommand()
  const pendingStops = route.status === 'EN_CURSO' ? route.packageCount - route.delivered - route.failed : route.stopCount
  const possible = pendingStops > 1
  return <button className="route-button" type="button" disabled={!possible || command.isPending}
    title={possible ? 'Ordena las paradas por el camino más rápido por calles' : 'Con una sola parada no hay nada que ordenar'}
    aria-label={`Optimizar el recorrido de ${route.driver.name}`}
    onClick={() => command.mutate({ id: route.id, action: 'optimize' }, {
      onSuccess: (result) => showToast(result.message || 'Recorrido optimizado.'),
      onError: (error) => showToast(error.message, 'error'),
    })}>
    {command.isPending ? <LoaderCircle size={16} className="loading-icon" aria-hidden="true" /> : <WandSparkles size={16} aria-hidden="true" />}
    {command.isPending ? 'Optimizando…' : 'Optimizar'}
  </button>
}
