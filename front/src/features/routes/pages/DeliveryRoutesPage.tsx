import { useState } from 'react'
import { CalendarDays, MapPinned, RefreshCw, Route, Truck } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { useAppSelector } from '../../../app/store'
import { selectCurrentUser } from '../../auth/redux/authSlice'
import { useBranches } from '../../shipments/hooks/useBranches'
import { DeliveryRouteDetail } from '../components/DeliveryRouteDetail'
import { DriverProfiles } from '../components/DriverProfiles'
import { RouteAlerts } from '../components/RouteAlerts'
import { RouteError, RouteLoading } from '../components/RouteFeedback'
import { RouteGenerationForm } from '../components/RouteGenerationForm'
import { useDrivers, useRoutes, useRoutesBusy } from '../hooks/useRoutes'
import { distanceLabels, formatRouteDistance, formatRouteDuration, localToday, routeStatusLabels } from '../routePresentation'
import type { DistanceType, GenerationResult, RouteFilters, RouteStatus } from '../types/route.types'
import './DeliveryRoutesPage.css'

export function DeliveryRoutesPage() {
  const [filters, setFilters] = useState<RouteFilters>({ branchId: 0, date: localToday(), distanceType: 'CORTA' })
  const [status, setStatus] = useState('')
  const [driverFilter, setDriverFilter] = useState('')
  const [editing, setEditing] = useState(false)
  const [params, setParams] = useSearchParams()
  const selectedId = params.get('recorrido') ?? ''
  const branches = useBranches()
  const drivers = useDrivers()
  const routes = useRoutes(filters)
  const busy = useRoutesBusy()
  const user = useAppSelector(selectCurrentUser)
  const disabled = busy || editing
  const visibleRoutes = routes.data?.filter((route) => (!status || route.status === status) && (!driverFilter || route.driver.id === driverFilter)) ?? []

  function selectRoute(id: string) {
    setParams(id ? { recorrido: id } : {}, { replace: true })
    setEditing(false)
  }

  function changeFilters(next: Partial<RouteFilters>) {
    setFilters((current) => ({ ...current, ...next }))
    selectRoute('')
    setDriverFilter('')
  }

  function generated(result: GenerationResult) {
    setStatus(''); setDriverFilter('')
    selectRoute(result.routes[0]?.id ?? '')
  }

  return <main className="delivery-routes-page">
    <header className="delivery-routes-page__intro"><span className="eyebrow"><Truck size={16} aria-hidden="true" /> Logística y distribución</span><h1>Gestionar recorridos</h1><p>Planificá el reparto, revisá las paradas y detectá los paquetes que necesitan una asignación.</p></header>
    <section className="route-panel" aria-labelledby="route-filters-title">
      <div className="route-panel__heading"><CalendarDays size={22} aria-hidden="true" /><div><h2 id="route-filters-title">Planificación del día</h2><p>La corta distancia entrega en domicilios. La larga distancia traslada paquetes entre sucursales.</p></div></div>
      <fieldset className="route-form-grid route-fieldset" disabled={disabled}>
        <div className="form-field"><label htmlFor="routes-branch">Sucursal de partida</label><select id="routes-branch" className="form-control" value={filters.branchId} onChange={(event) => changeFilters({ branchId: Number(event.target.value) })} disabled={disabled || branches.isPending || branches.isError}><option value={0}>Todas las sucursales</option>{branches.data?.map((branch) => <option key={branch.id} value={branch.id}>{branch.name}</option>)}</select></div>
        <div className="form-field"><label htmlFor="routes-date">Fecha de reparto</label><input className="form-control" id="routes-date" type="date" value={filters.date} onChange={(event) => changeFilters({ date: event.target.value })} required /></div>
        <div className="form-field"><label htmlFor="routes-distance">Tipo de recorrido</label><select className="form-control" id="routes-distance" value={filters.distanceType} onChange={(event) => changeFilters({ distanceType: event.target.value as DistanceType })}><option value="CORTA">Corta distancia · domicilios</option><option value="LARGA">Larga distancia · sucursales</option></select></div>
      </fieldset>
      {branches.isPending && <RouteLoading label="Cargando sucursales…" />}
      {branches.isError && <RouteError error={branches.error} onRetry={() => void branches.refetch()} pending={branches.isFetching} />}
      {drivers.isPending && <RouteLoading label="Cargando repartidores…" />}
      {drivers.isError && <RouteError error={drivers.error} onRetry={() => void drivers.refetch()} pending={drivers.isFetching} />}
    </section>

    {drivers.data && <DriverProfiles drivers={drivers.data} branches={branches.data ?? []} busy={disabled || branches.isPending || branches.isError} canCreateUser={user?.role === 'SUPERADMIN'} />}
    <RouteGenerationForm key={`${filters.branchId}:${filters.date}:${filters.distanceType}`} filters={filters} drivers={drivers.data ?? []} routes={routes.data ?? []} busy={disabled || drivers.isPending || drivers.isError || branches.isError} onGenerated={generated} />

    <section className="route-panel" aria-labelledby="routes-list-title">
      <div className="route-panel__heading"><Route size={22} aria-hidden="true" /><div><h2 id="routes-list-title">Recorridos planificados</h2><p>{distanceLabels[filters.distanceType]} · {filters.date || 'Elegí una fecha'}</p></div><button className="route-button" type="button" disabled={disabled || routes.isFetching || !filters.date} onClick={() => void routes.refetch()}><RefreshCw size={17} aria-hidden="true" /> Actualizar recorridos</button></div>
      <div className="route-list-filters"><div className="form-field"><label htmlFor="routes-status">Filtrar recorridos por estado</label><select id="routes-status" className="form-control" value={status} disabled={disabled} onChange={(event) => setStatus(event.target.value)}><option value="">Todos los estados</option>{Object.entries(routeStatusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div><div className="form-field"><label htmlFor="routes-driver">Filtrar recorridos por repartidor</label><select id="routes-driver" className="form-control" value={driverFilter} disabled={disabled} onChange={(event) => setDriverFilter(event.target.value)}><option value="">Todos los repartidores</option>{drivers.data?.map((driver) => <option key={driver.id} value={driver.id}>{driver.name}</option>)}</select></div></div>
      {editing && <p className="route-warning" role="status">Guardá o cancelá la edición antes de cambiar de recorrido o de planificación.</p>}
      {!filters.date && <p className="route-empty">Elegí una fecha para consultar los recorridos.</p>}
      {routes.isPending && filters.date && <RouteLoading label="Consultando recorridos…" />}
      {routes.isError && <RouteError error={routes.error} onRetry={() => void routes.refetch()} pending={routes.isFetching} />}
      {routes.data && <div className={`route-workspace${!selectedId ? ' route-workspace--unselected' : ''}`}>
        <div className="route-list" aria-label="Lista de recorridos">
          {visibleRoutes.length === 0 && <p className="route-empty">No hay recorridos para estos filtros. Si vas a generar, asegurate de que los paquetes ya estén recibidos en sucursal y los repartidores tengan perfil activo.</p>}
          {visibleRoutes.map((route) => <button className={`route-card${selectedId === route.id ? ' is-selected' : ''}`} key={route.id} type="button" disabled={disabled} aria-pressed={selectedId === route.id} onClick={() => selectRoute(route.id)}>
            <span className="route-card__heading"><Truck size={20} aria-hidden="true" /><strong>{route.driver.name}</strong></span><span className="route-status">{routeStatusLabels[route.status as RouteStatus]}</span><small>{route.branchName} · #{route.id.slice(0, 8)}</small><span>{route.packageCount} paquetes · {route.stopCount} paradas</span><small>Planificación: ≈ {formatRouteDistance(route.distanceKm)} · {formatRouteDuration(route.durationMinutes)}</small>
          </button>)}
        </div>
        {!selectedId && visibleRoutes.length > 0 && <div className="route-empty"><MapPinned size={28} aria-hidden="true" /><p>Elegí un recorrido para ver su mapa y gestionar las paradas.</p></div>}
        {selectedId && <DeliveryRouteDetail key={selectedId} id={selectedId} drivers={drivers.data ?? []} busy={busy} editing={editing} onEditingChange={setEditing} onDeleted={() => selectRoute('')} />}
      </div>}
    </section>
    <RouteAlerts branchId={filters.branchId} busy={disabled} />
  </main>
}
