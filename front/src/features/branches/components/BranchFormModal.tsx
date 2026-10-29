import { useState, type FormEvent } from 'react'
import { Building2, CircleAlert, LoaderCircle, LocateFixed, MapPin, Save } from 'lucide-react'
import { Modal } from '../../../shared/components/Modal'
import { ShipmentMap } from '../../shipments/components/ShipmentMap'
import { useGeocodeDestination } from '../../shipments/hooks/useGeocodeDestination'
import type { AdminBranch, BranchInput } from '../types/branch.types'

interface BranchFormModalProps {
  open: boolean
  /** Sucursal a editar; sin ella, se da de alta una nueva. */
  branch: AdminBranch | null
  pending: boolean
  error: string | null
  onClose: () => void
  onSubmit: (input: BranchInput) => void
}

export function BranchFormModal(props: BranchFormModalProps) {
  return (
    <Modal
      open={props.open}
      onClose={props.onClose}
      size="wide"
      icon={Building2}
      eyebrow={props.branch ? 'Editar sucursal' : 'Nueva sucursal'}
      title={props.branch ? props.branch.name : 'Registrar sucursal'}
      description="La dirección es el punto de partida de los recorridos: ubicala en el mapa y ajustá el marcador si hace falta."
    >
      <BranchForm key={props.branch?.id ?? 'nueva'} {...props} />
    </Modal>
  )
}

/** "San Martín 1450" → calle y altura, para ubicarla con Georef. */
function splitAddress(address: string) {
  const match = address.trim().match(/^(.*?)\s+(\d+)\s*$/)
  return match ? { street: match[1], streetNumber: match[2] } : { street: address.trim(), streetNumber: '' }
}

function BranchForm({ branch, pending, error, onClose, onSubmit }: BranchFormModalProps) {
  const [name, setName] = useState(branch?.name ?? '')
  const [province, setProvince] = useState(branch?.province ?? '')
  const [city, setCity] = useState(branch?.city ?? '')
  const [address, setAddress] = useState(branch?.address ?? '')
  const [active, setActive] = useState(branch?.active ?? true)
  const [point, setPoint] = useState<{ latitude: number; longitude: number } | null>(
    branch?.latitude != null && branch.longitude != null ? { latitude: branch.latitude, longitude: branch.longitude } : null,
  )
  const [located, setLocated] = useState<string | null>(null)
  const geocode = useGeocodeDestination()

  function changeAddress(setter: (value: string) => void, value: string) {
    setter(value)
    // Si cambia la dirección, hay que volver a ubicarla.
    setPoint(null)
    setLocated(null)
    geocode.reset()
  }

  function locate() {
    if (city.trim().length < 2) return
    geocode.mutate({ ...splitAddress(address), city, province }, {
      onSuccess: (result) => {
        setPoint({ latitude: result.latitude, longitude: result.longitude })
        setLocated(result.precision === 'address' ? result.label : `${result.label} (solo la ciudad: ajustá el marcador)`)
      },
    })
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!point) return
    onSubmit({
      name: name.trim(),
      province: province.trim(),
      city: city.trim(),
      address: address.trim(),
      latitude: point.latitude,
      longitude: point.longitude,
      active,
    })
  }

  return (
    <form className="branch-form" onSubmit={handleSubmit}>
      <div className="branch-form__grid">
        <div className="form-field branch-form__full">
          <label htmlFor="branch-name">Nombre</label>
          <input className="form-control" id="branch-name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Ej. Sucursal Villa María" minLength={2} maxLength={150} required autoFocus />
        </div>
        <div className="form-field">
          <label htmlFor="branch-province">Provincia</label>
          <input className="form-control" id="branch-province" value={province} onChange={(event) => changeAddress(setProvince, event.target.value)} minLength={2} maxLength={100} required />
        </div>
        <div className="form-field">
          <label htmlFor="branch-city">Ciudad</label>
          <input className="form-control" id="branch-city" value={city} onChange={(event) => changeAddress(setCity, event.target.value)} minLength={2} maxLength={100} required />
        </div>
        <div className="form-field branch-form__full">
          <label htmlFor="branch-address">Dirección (calle y altura)</label>
          <div className="branch-form__locate">
            <input className="form-control" id="branch-address" value={address} onChange={(event) => changeAddress(setAddress, event.target.value)} placeholder="Ej. San Martín 1450" minLength={3} maxLength={255} required />
            <button className="btn" type="button" onClick={locate} disabled={geocode.isPending || city.trim().length < 2 || address.trim().length < 3}>
              {geocode.isPending ? <LoaderCircle className="loading-icon" size={17} aria-hidden="true" /> : <LocateFixed size={17} aria-hidden="true" />}
              Ubicar en el mapa
            </button>
          </div>
          {geocode.isError && <span className="form-error" role="alert"><CircleAlert size={15} aria-hidden="true" /> {geocode.error.message} Podés marcar el punto con un clic en el mapa.</span>}
          {located && <span className="branch-form__hint" role="status"><MapPin size={14} aria-hidden="true" /> {located}</span>}
        </div>
      </div>

      <ShipmentMap
        mode="picker"
        latitude={point?.latitude ?? null}
        longitude={point?.longitude ?? null}
        accessibleName="Ubicación de la sucursal: hacé clic o arrastrá el marcador"
        initialCenter={{ latitude: -31.42, longitude: -64.18 }}
        onLocationChange={(latitude, longitude) => setPoint({ latitude, longitude })}
      />
      <p className="branch-form__hint">
        {point ? 'De este punto salen los recorridos de la sucursal.' : 'Ubicá la dirección o marcá el punto en el mapa: es obligatorio.'}
      </p>

      <label className="branch-form__check" htmlFor="branch-active">
        <input id="branch-active" type="checkbox" checked={active} onChange={(event) => setActive(event.target.checked)} />
        <span><strong>Sucursal activa</strong><small>Si la desactivás, deja de ofrecerse para envíos nuevos y nadie más puede elegirla, salvo el Superadministrador.</small></span>
      </label>

      {error && <p className="form-error" role="alert"><CircleAlert size={18} aria-hidden="true" /> {error}</p>}

      <div className="branch-form__actions">
        <button className="btn btn--ghost" type="button" onClick={onClose}>Cancelar</button>
        <button className="btn btn--primary" type="submit" disabled={pending || !point}>
          {pending ? <LoaderCircle className="loading-icon" size={18} aria-hidden="true" /> : <Save size={18} aria-hidden="true" />}
          {pending ? 'Guardando…' : branch ? 'Guardar cambios' : 'Registrar sucursal'}
        </button>
      </div>
    </form>
  )
}
