import { useState, type FormEvent } from 'react'
import { CheckCircle2, LoaderCircle, Save, UsersRound } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { Branch } from '../../shipments/types/shipment.types'
import { useSaveDriverProfile } from '../hooks/useRoutes'
import { distanceLabels } from '../routePresentation'
import type { DistanceType, Driver } from '../types/route.types'
import { RouteError } from './RouteFeedback'

function ProfileForm({ driver, branches, busy }: { driver: Driver; branches: Branch[]; busy: boolean }) {
  const [branchId, setBranchId] = useState(driver.branch?.id ?? 0)
  const [distanceType, setDistanceType] = useState<DistanceType>(driver.distanceType ?? 'CORTA')
  const [active, setActive] = useState(driver.active ?? true)
  const mutation = useSaveDriverProfile()
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!branchId || busy) return
    mutation.mutate({ driverId: driver.id, branchId, distanceType, active })
  }
  return <form className="route-profile-form" onSubmit={submit}>
    <p className="route-hint">{driver.configured ? `${driver.branch?.name} · ${driver.distanceType ? distanceLabels[driver.distanceType] : ''}` : 'Este usuario todavía no tiene perfil operativo.'} Cuenta: {driver.accountStatus}.</p>
    <fieldset className="route-form-grid route-fieldset" disabled={busy}>
      <div className="form-field"><label htmlFor="driver-profile-branch">Sucursal base</label><select className="form-control" id="driver-profile-branch" value={branchId || ''} onChange={(event) => setBranchId(Number(event.target.value))} required><option value="">Seleccioná una sucursal</option>{branches.map((branch) => <option key={branch.id} value={branch.id}>{branch.name}</option>)}</select></div>
      <div className="form-field"><label htmlFor="driver-profile-type">Tipo de reparto del perfil</label><select className="form-control" id="driver-profile-type" value={distanceType} onChange={(event) => setDistanceType(event.target.value as DistanceType)}><option value="CORTA">Corta distancia</option><option value="LARGA">Larga distancia</option></select></div>
      <label className="route-check"><input type="checkbox" checked={active} onChange={(event) => setActive(event.target.checked)} /> Perfil activo para recibir recorridos</label>
    </fieldset>
    {mutation.isError && <RouteError error={mutation.error} />}
    {mutation.isSuccess && <p className="route-success" role="status"><CheckCircle2 size={18} aria-hidden="true" /> Perfil guardado.</p>}
    <button className="route-button" type="submit" disabled={busy || !branchId}>{mutation.isPending ? <LoaderCircle size={18} className="loading-icon" aria-hidden="true" /> : <Save size={18} aria-hidden="true" />} Guardar perfil</button>
  </form>
}

export function DriverProfiles({ drivers, branches, busy, canCreateUser }: { drivers: Driver[]; branches: Branch[]; busy: boolean; canCreateUser: boolean }) {
  const [selectedId, setSelectedId] = useState('')
  const driver = drivers.find((item) => item.id === selectedId)
  return <details className="route-panel route-profiles">
    <summary><UsersRound size={21} aria-hidden="true" /><span><strong>Repartidores</strong><small>Configurá la sucursal base y el tipo de reparto antes de generar.</small></span></summary>
    <div className="route-profiles__body">
      {drivers.length === 0 ? <p>No hay usuarios con rol Repartidor. {canCreateUser ? <Link to="/admin/usuarios/nuevo">Registrar un repartidor</Link> : 'Pedile al superadministrador que registre los usuarios.'}</p> : <>
        <div className="form-field"><label htmlFor="driver-profile-user">Repartidor a configurar</label><select id="driver-profile-user" className="form-control" value={selectedId} onChange={(event) => setSelectedId(event.target.value)} disabled={busy}><option value="">Seleccioná un repartidor</option>{drivers.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.configured ? item.available ? 'Perfil activo' : 'No disponible' : 'Sin perfil'}</option>)}</select></div>
        {driver && <ProfileForm key={driver.id} driver={driver} branches={branches} busy={busy} />}
      </>}
    </div>
  </details>
}
