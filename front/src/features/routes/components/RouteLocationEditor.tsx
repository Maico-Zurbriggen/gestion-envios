import { useEffect, useRef, useState, type FormEvent } from 'react'
import { CircleAlert, LoaderCircle, MapPin, Save, X } from 'lucide-react'
import { ShipmentMap } from '../../shipments/components/ShipmentMap'
import type { DeliveryRoute, RouteStop } from '../types/route.types'

function coordinate(value: string, limit: number): number | null {
  if (!value.trim()) return null
  const parsed = Number(value)
  return Number.isFinite(parsed) && Math.abs(parsed) <= limit ? parsed : null
}

export function RouteLocationEditor({ route, stop, busy, onSave, onCancel }: {
  route: DeliveryRoute
  stop: RouteStop
  busy: boolean
  onSave: (latitude: number, longitude: number) => Promise<void>
  onCancel: () => void
}) {
  const heading = useRef<HTMLHeadingElement>(null)
  const [latitude, setLatitude] = useState('')
  const [longitude, setLongitude] = useState('')
  const [message, setMessage] = useState('')
  const lat = coordinate(latitude, 90)
  const lon = coordinate(longitude, 180)
  const initialCenter = route.branch.latitude != null && route.branch.longitude != null
    ? { latitude: route.branch.latitude, longitude: route.branch.longitude } : undefined

  useEffect(() => { heading.current?.focus() }, [])

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy || lat === null || lon === null) return
    setMessage('')
    try { await onSave(lat, lon) }
    catch (error) { setMessage(error instanceof Error ? error.message : 'No pudimos guardar la ubicación.') }
  }

  return <section className="route-editor route-location-editor" aria-labelledby="route-location-title">
    <h3 id="route-location-title" ref={heading} tabIndex={-1}><MapPin size={20} aria-hidden="true" /> Ubicar domicilio</h3>
    <p><strong>{stop.destination}</strong></p>
    <p className="route-hint">Marcá la dirección exacta haciendo clic en el mapa o ingresá sus coordenadas. La ubicación se guardará para todos los paquetes de este envío.</p>
    <p className="route-hint">El mapa comienza en la sucursal de partida. Ese punto no es la ubicación del destinatario.</p>
    <fieldset className="route-fieldset" disabled={busy}>
      <div className="route-location-editor__map" aria-busy={busy}>
        <ShipmentMap latitude={lat !== null && lon !== null ? lat : null} longitude={lat !== null && lon !== null ? lon : null} mode="picker" initialCenter={initialCenter} accessibleName={`Seleccionar ubicación de ${stop.destination}`} onLocationChange={(nextLat, nextLon) => { if (!busy) { setLatitude(nextLat.toFixed(6)); setLongitude(nextLon.toFixed(6)) } }} />
      </div>
      <form onSubmit={(event) => void save(event)}>
        <div className="route-form-grid">
          <div className="form-field"><label htmlFor="route-location-latitude">Latitud</label><input className="form-control" id="route-location-latitude" type="number" step="any" min={-90} max={90} value={latitude} onChange={(event) => setLatitude(event.target.value)} required /></div>
          <div className="form-field"><label htmlFor="route-location-longitude">Longitud</label><input className="form-control" id="route-location-longitude" type="number" step="any" min={-180} max={180} value={longitude} onChange={(event) => setLongitude(event.target.value)} required /></div>
        </div>
        <p className="route-hint" role="status">{lat !== null && lon !== null ? `Punto seleccionado: ${lat.toFixed(6)}, ${lon.toFixed(6)}.` : 'Todavía no seleccionaste un punto. Si el mapa no carga, podés ingresar las coordenadas.'}</p>
        {message && <p className="form-error" role="alert"><CircleAlert size={18} aria-hidden="true" />{message}</p>}
        <div className="route-actions"><button className="route-button route-button--primary" type="submit" disabled={busy || lat === null || lon === null}>{busy ? <LoaderCircle size={18} className="loading-icon" aria-hidden="true" /> : <Save size={18} aria-hidden="true" />} Guardar ubicación</button><button className="route-button" type="button" onClick={onCancel}><X size={18} aria-hidden="true" /> Cancelar</button></div>
      </form>
    </fieldset>
  </section>
}
