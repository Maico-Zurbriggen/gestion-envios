import { useState, type FormEvent } from 'react'
import { CheckCircle2, CircleAlert, LoaderCircle, Sparkles } from 'lucide-react'
import { useGenerateRoutes } from '../hooks/useRoutes'
import { isRouteEditable } from '../routePresentation'
import type { DeliveryRouteSummary, Driver, GenerateRoutesInput, GenerationResult, RouteFilters } from '../types/route.types'
import { ConfirmRouteAction } from './ConfirmRouteAction'
import { RouteError } from './RouteFeedback'

export function RouteGenerationForm({ filters, drivers, routes, busy, onGenerated }: {
  filters: RouteFilters
  drivers: Driver[]
  routes: DeliveryRouteSummary[]
  busy: boolean
  onGenerated: (result: GenerationResult) => void
}) {
  const [orientation, setOrientation] = useState('0')
  const [customDrivers, setCustomDrivers] = useState(false)
  const [driverIds, setDriverIds] = useState<string[]>([])
  const [replace, setReplace] = useState(false)
  const [message, setMessage] = useState('')
  const [confirmation, setConfirmation] = useState<GenerateRoutesInput | null>(null)
  const mutation = useGenerateRoutes()
  const eligibleDrivers = drivers.filter((driver) => driver.available && driver.branch?.id === filters.branchId && driver.distanceType === filters.distanceType)
  const replaceable = routes.filter((route) => route.branchId === filters.branchId && isRouteEditable(route.status)).length

  function generate(input: GenerateRoutesInput) {
    mutation.mutate(input, {
      onSuccess: (result) => { setConfirmation(null); onGenerated(result) },
      onError: () => setConfirmation(null),
    })
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    const angle = filters.distanceType === 'CORTA' ? Number(orientation) : 0
    if (!filters.branchId || !filters.date) { setMessage('Elegí una sucursal y una fecha para generar.'); return }
    if (!orientation.trim() || !Number.isFinite(angle) || angle < 0 || angle >= 90) { setMessage('La orientación debe ser un número desde 0 y menor que 90.'); return }
    if (customDrivers && (!driverIds.length || driverIds.length > 100)) { setMessage('Elegí entre 1 y 100 repartidores.'); return }
    setMessage('')
    const input: GenerateRoutesInput = { ...filters, streetOrientation: angle, driverIds: customDrivers ? driverIds : null, replaceExisting: replace }
    if (replace && replaceable > 0) setConfirmation(input)
    else generate(input)
  }

  return <section className="route-panel" aria-labelledby="generation-title">
    <div className="route-panel__heading"><Sparkles size={22} aria-hidden="true" /><div><h2 id="generation-title">Generación automática</h2><p>Distribuí los paquetes listos en sucursal y ordená las visitas entre los repartidores disponibles.</p></div></div>
    <form className="route-generation" onSubmit={submit}>
      <fieldset disabled={busy || !filters.branchId} className="route-fieldset">
        {filters.distanceType === 'CORTA' && <div className="form-field route-generation__angle">
          <label htmlFor="route-orientation">Orientación de las calles (grados)</label>
          <input className="form-control" id="route-orientation" type="number" min={0} max={90} step="any" value={orientation} onChange={(event) => setOrientation(event.target.value)} required aria-describedby="route-orientation-help" />
          <small id="route-orientation-help">Desde 0 y menor que 90, respecto del norte. Se usa para estimar distancias dentro de la ciudad.</small>
        </div>}
        <label className="route-check"><input type="checkbox" checked={customDrivers} onChange={(event) => setCustomDrivers(event.target.checked)} /> Elegir repartidores para esta generación</label>
        {customDrivers && <div className="route-driver-options" role="group" aria-label="Repartidores para generar">
          {eligibleDrivers.length ? eligibleDrivers.map((driver) => <label className="route-check" key={driver.id}>
            <input type="checkbox" checked={driverIds.includes(driver.id)} onChange={(event) => setDriverIds((ids) => event.target.checked ? [...ids, driver.id] : ids.filter((id) => id !== driver.id))} />{driver.name}
          </label>) : <p>No hay perfiles activos para esta sucursal y tipo. Configuralos en «Repartidores».</p>}
        </div>}
        <p className="route-hint">{customDrivers ? 'Al generar se comprueba que cada repartidor esté libre para esta fecha.' : 'Se usarán los repartidores activos de esta sucursal y tipo que estén libres para la fecha elegida.'}</p>
        <label className="route-check"><input type="checkbox" checked={replace} onChange={(event) => setReplace(event.target.checked)} /> Reemplazar recorridos sin iniciar</label>
        {replace && <p className="route-hint">Se descartarán los recorridos generados o en edición de esta sucursal, fecha y tipo. Los recorridos en curso se conservan.</p>}
      </fieldset>
      {!filters.branchId && <p className="route-hint">Elegí una sucursal de partida en los filtros para generar recorridos.</p>}
      {message && <p className="form-error" role="alert"><CircleAlert size={18} aria-hidden="true" />{message}</p>}
      {mutation.isError && <RouteError error={mutation.error} />}
      <button className="route-button route-button--primary" type="submit" disabled={busy || !filters.branchId || !filters.date}>
        {mutation.isPending ? <LoaderCircle className="loading-icon" size={18} aria-hidden="true" /> : <Sparkles size={18} aria-hidden="true" />}{mutation.isPending ? 'Generando…' : 'Generar recorridos'}
      </button>
    </form>
    {mutation.data && <div className="route-generation__result" role="status">
      <p><CheckCircle2 size={20} aria-hidden="true" />{mutation.data.message}</p>
      <dl className="route-stats"><div><dt>Asignados</dt><dd>{mutation.data.summary.assigned}</dd></div><div><dt>Sin recorrido</dt><dd>{mutation.data.summary.unassigned}</dd></div><div><dt>Recorridos</dt><dd>{mutation.data.summary.generated}</dd></div></dl>
    </div>}
    {confirmation && <ConfirmRouteAction title="¿Reemplazar la planificación?" description={`Se descartarán ${replaceable} recorrido(s) sin iniciar y se volverán a distribuir sus paquetes. La edición manual anterior se perderá.`} confirmLabel="Reemplazar y generar" pending={busy} onConfirm={() => generate(confirmation)} onCancel={() => setConfirmation(null)} />}
  </section>
}
