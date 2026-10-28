import { useState, type FormEvent } from 'react'
import { LoaderCircle, Plus, Route } from 'lucide-react'
import { Modal } from '../../../shared/components/Modal'
import { useCreateRoute, usePendingPackages } from '../hooks/useRoutes'
import { dayParts } from '../routePresentation'
import type { DistanceType, Driver } from '../types/route.types'
import { PendingPackagesPicker } from './PendingPackagesPicker'
import { RouteError, RouteLoading } from './RouteFeedback'

/** Alta manual: un repartidor libre ese día y los paquetes que lleva. Después se ordenan en el recorrido. */
export function NewRouteModal({ branchId, branchName, date, distanceType, drivers, busyDriverIds, onClose, onCreated }: {
  branchId: number
  branchName: string
  date: string
  distanceType: DistanceType
  drivers: Driver[]
  /** Repartidores que ya tienen un recorrido activo ese día. */
  busyDriverIds: Set<string>
  onClose: () => void
  onCreated: (routeId: string, day: string) => void
}) {
  const pending = usePendingPackages(branchId, distanceType)
  const create = useCreateRoute()
  const free = drivers.filter((driver) => !busyDriverIds.has(driver.id))
  const [driverId, setDriverId] = useState(() => (free.length === 1 ? free[0].id : ''))
  const [selected, setSelected] = useState<Set<string>>(() => new Set())
  const [day, setDay] = useState(date)

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!driverId || !selected.size || create.isPending) return
    // Se respeta el orden de la lista; después se puede optimizar o reordenar.
    const packages = (pending.data ?? []).filter((item) => selected.has(item.code)).map((item) => item.code)
    create.mutate({ branchId, date: day, distanceType, driverId, packages }, { onSuccess: (route) => onCreated(route.id, day) })
  }

  return <Modal open onClose={create.isPending ? () => {} : onClose} eyebrow={branchName} title="Nuevo recorrido" icon={Route} size="wide"
    description="Elegí el repartidor y los paquetes que lleva. Después los podés ordenar a mano o con «Optimizar»."
    footer={<>
      <button className="route-button" type="button" onClick={onClose} disabled={create.isPending}>Cancelar</button>
      <button className="route-button route-button--primary" type="submit" form="new-route-form" disabled={!driverId || !selected.size || create.isPending}>
        {create.isPending ? <LoaderCircle size={17} className="loading-icon" aria-hidden="true" /> : <Plus size={17} aria-hidden="true" />}
        {selected.size ? `Crear con ${selected.size} ${selected.size === 1 ? 'paquete' : 'paquetes'}` : 'Crear recorrido'}
      </button>
    </>}>
    <form id="new-route-form" className="route-modal-form" onSubmit={submit}>
      <div className="route-modal-form__row">
        <div className="form-field">
          <label htmlFor="new-route-day">Sale el día</label>
          <input id="new-route-day" className="form-control" type="date" value={day} onChange={(event) => event.target.value && setDay(event.target.value)} required disabled={create.isPending} />
          <small className="route-hint">{dayParts(day).long}</small>
        </div>
        <div className="form-field">
          <label htmlFor="new-route-driver">Repartidor</label>
          <select id="new-route-driver" className="form-control" value={driverId} onChange={(event) => setDriverId(event.target.value)} required disabled={create.isPending}>
            <option value="">Elegí un repartidor</option>
            {drivers.map((driver) => <option key={driver.id} value={driver.id} disabled={busyDriverIds.has(driver.id)}>
              {driver.name}{busyDriverIds.has(driver.id) ? ' · ya tiene recorrido ese día' : ''}
            </option>)}
          </select>
          {!drivers.length && <small className="route-hint">No hay repartidores activos con base en esta sucursal para este tipo de reparto. Configuralos en «Repartidores».</small>}
        </div>
      </div>
      <fieldset className="route-fieldset">
        <legend className="route-modal-form__legend">Paquetes que esperan recorrido</legend>
        {pending.isPending && <RouteLoading label="Buscando paquetes en espera…" />}
        {pending.isError && <RouteError error={pending.error} onRetry={() => void pending.refetch()} pending={pending.isFetching} />}
        {pending.data && <PendingPackagesPicker packages={pending.data} selected={selected} onChange={setSelected} disabled={create.isPending} />}
      </fieldset>
      {create.isError && <RouteError error={create.error} />}
    </form>
  </Modal>
}
