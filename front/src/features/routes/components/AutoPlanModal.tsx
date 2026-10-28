import { useState } from 'react'
import { CheckCircle2, CircleAlert, Cpu, LoaderCircle, Package, UserRound } from 'lucide-react'
import { Modal } from '../../../shared/components/Modal'
import { useGenerateRoutes, usePendingPackages } from '../hooks/useRoutes'
import { dayParts, formatRouteDistance, formatRouteDuration } from '../routePresentation'
import type { DistanceType, Driver, GenerationResult } from '../types/route.types'
import { RouteError, RouteLoading } from './RouteFeedback'

/**
 * Reparte entre los repartidores elegidos los paquetes que todavía esperan recorrido.
 * Lo que ya está armado no se toca. Cada recorrido sale ordenado para minimizar el tiempo.
 */
export function AutoPlanModal({ branchId, branchName, date, distanceType, drivers, busyDriverIds, onClose, onDone }: {
  branchId: number
  branchName: string
  date: string
  distanceType: DistanceType
  drivers: Driver[]
  busyDriverIds: Set<string>
  onClose: () => void
  onDone: (firstRouteId: string | null) => void
}) {
  const pending = usePendingPackages(branchId, distanceType)
  const generate = useGenerateRoutes()
  const [chosen, setChosen] = useState<Set<string>>(() => new Set(drivers.filter((d) => !busyDriverIds.has(d.id)).map((d) => d.id)))
  const [result, setResult] = useState<GenerationResult | null>(null)
  const plannable = pending.data?.filter((item) => item.located).length ?? 0

  function toggle(id: string) {
    setChosen((current) => {
      const next = new Set(current)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function run() {
    generate.mutate({ branchId, date, distanceType, driverIds: [...chosen] }, { onSuccess: setResult })
  }

  const title = `${branchName} · ${dayParts(date).long}`

  if (result) {
    return <Modal open onClose={() => onDone(result.routes[0]?.id ?? null)} eyebrow={title} title="Recorridos armados" icon={Cpu} size="wide"
      description="Quedaron listos para revisar. Podés reordenar las paradas, sumar o quitar paquetes antes de que salgan."
      footer={<button className="route-button route-button--primary" type="button" onClick={() => onDone(result.routes[0]?.id ?? null)}><CheckCircle2 size={17} aria-hidden="true" /> Ver los recorridos</button>}>
      <div className="route-modal-form">
        <p className="route-success" role="status"><CheckCircle2 size={18} aria-hidden="true" />{result.message}</p>
        {result.routes.length > 0 && <ul className="route-result-list">
          {result.routes.map((route) => <li key={route.id}>
            <UserRound size={18} aria-hidden="true" />
            <span><strong>{route.driver.name}</strong><small>{route.packageCount} paquetes · {route.stopCount} paradas · {formatRouteDistance(route.distanceKm)} · {formatRouteDuration(route.durationMinutes)}</small></span>
          </li>)}
        </ul>}
        {result.alerts.length > 0 && <>
          <p className="route-modal-form__legend">Quedaron esperando ({result.alerts.length})</p>
          <ul className="route-result-list route-result-list--warning">
            {result.alerts.map((alert) => <li key={alert.id}>
              <CircleAlert size={18} aria-hidden="true" />
              <span><strong className="route-code">{alert.packageNumber}</strong><small>{alert.description}</small></span>
            </li>)}
          </ul>
          <p className="route-hint">Los podés sumar a mano a un recorrido con «Agregar», o corregir lo que falte (por ejemplo, la ubicación del domicilio).</p>
        </>}
      </div>
    </Modal>
  }

  return <Modal open onClose={generate.isPending ? () => {} : onClose} eyebrow={title} title="Armar automáticamente" icon={Cpu} size="wide"
    description="Reparte los paquetes que esperan recorrido entre los repartidores que elijas y ordena cada recorrido. Lo que ya está armado no se toca."
    footer={<>
      <button className="route-button" type="button" onClick={onClose} disabled={generate.isPending}>Cancelar</button>
      <button className="route-button route-button--primary" type="button" onClick={run} disabled={generate.isPending || !chosen.size || !pending.data?.length}>
        {generate.isPending ? <LoaderCircle size={17} className="loading-icon" aria-hidden="true" /> : <Cpu size={17} aria-hidden="true" />}
        {generate.isPending ? 'Armando…' : 'Armar recorridos'}
      </button>
    </>}>
    <div className="route-modal-form">
      {pending.isPending && <RouteLoading label="Contando los paquetes en espera…" />}
      {pending.isError && <RouteError error={pending.error} onRetry={() => void pending.refetch()} pending={pending.isFetching} />}
      {pending.data && <dl className="route-plan-summary">
        <div><dt><Package size={16} aria-hidden="true" /> Esperan recorrido</dt><dd>{pending.data.length}</dd></div>
        <div><dt><UserRound size={16} aria-hidden="true" /> Repartidores elegidos</dt><dd>{chosen.size}</dd></div>
        <div><dt><CircleAlert size={16} aria-hidden="true" /> Sin ubicación</dt><dd>{pending.data.length - plannable}</dd></div>
      </dl>}
      {pending.data?.length === 0 && <p className="route-empty">No hay paquetes esperando recorrido en esta sucursal.</p>}
      <fieldset className="route-fieldset">
        <legend className="route-modal-form__legend">Repartidores</legend>
        {drivers.length === 0
          ? <p className="route-hint">No hay repartidores activos con base en esta sucursal para este tipo de reparto. Configuralos en «Repartidores».</p>
          : <ul className="route-driver-list">
            {drivers.map((driver) => {
              const busy = busyDriverIds.has(driver.id)
              return <li key={driver.id}>
                <label className={`route-check${busy ? ' is-disabled' : ''}`}>
                  <input type="checkbox" checked={!busy && chosen.has(driver.id)} disabled={busy || generate.isPending} onChange={() => toggle(driver.id)} />
                  <span>{driver.name}{busy && <small> · ya tiene recorrido ese día</small>}</span>
                </label>
              </li>
            })}
          </ul>}
      </fieldset>
      <p className="route-hint">Los paquetes sin ubicación en el mapa no se pueden repartir automáticamente: quedan esperando para sumarlos a mano.</p>
      {generate.isError && <RouteError error={generate.error} />}
    </div>
  </Modal>
}
