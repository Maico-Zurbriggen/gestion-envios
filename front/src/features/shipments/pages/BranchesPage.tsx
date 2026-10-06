import { useState } from 'react'
import { ArrowLeft, Building2, CircleAlert, LoaderCircle, MapPin, MapPinned, RefreshCw } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useBranches } from '../hooks/useBranches'
import { ShipmentMap } from '../components/ShipmentMap'
import type { Branch } from '../types/shipment.types'
import './BranchesPage.css'

export function BranchesPage() {
  const branchesQuery = useBranches()
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const selectedBranch = branchesQuery.data?.find((branch) => branch.id === selectedId) ?? null

  return (
    <main className="branches-page">
      <div className="branches-page__content">
        <Link className="branches-page__back" to="/envios/nuevo"><ArrowLeft size={18} aria-hidden="true" /> Volver al registro</Link>
        <header className="branches-page__intro">
          <span className="eyebrow"><Building2 size={16} aria-hidden="true" /> Retiro en sucursal</span>
          <h1>Sucursales disponibles</h1>
          <p>Elegí dónde querés que el destinatario retire el envío. Podés consultar la dirección y ubicación de cada sucursal sin iniciar sesión.</p>
        </header>

        {branchesQuery.isPending && <p className="branches-page__feedback" role="status"><LoaderCircle className="loading-icon" size={20} aria-hidden="true" /> Cargando sucursales…</p>}
        {branchesQuery.isError && (
          <div className="branches-page__feedback" role="alert">
            <CircleAlert size={22} aria-hidden="true" />
            <span>{branchesQuery.error.message}</span>
            <button type="button" onClick={() => void branchesQuery.refetch()} disabled={branchesQuery.isFetching}><RefreshCw size={16} aria-hidden="true" /> Reintentar</button>
          </div>
        )}
        {branchesQuery.data?.length === 0 && <p className="branches-page__feedback" role="status">No hay sucursales disponibles para retiro en este momento.</p>}

        {branchesQuery.data && branchesQuery.data.length > 0 && (
          <div className="branches-page__layout">
            <div className="branches-page__list" aria-label="Sucursales disponibles">
              {branchesQuery.data.map((branch: Branch) => (
                <article className={`branches-page__card ${selectedId === branch.id ? 'is-selected' : ''}`} key={branch.id}>
                  <div className="branches-page__card-heading"><Building2 size={21} aria-hidden="true" /><h2>{branch.name}</h2></div>
                  <p><MapPin size={16} aria-hidden="true" /> {branch.address}, {branch.city}, {branch.province}</p>
                  <div className="branches-page__card-actions">
                    <button type="button" onClick={() => setSelectedId(branch.id)} aria-pressed={selectedId === branch.id}><MapPinned size={16} aria-hidden="true" /> Ver ubicación</button>
                    <Link to={`/envios/nuevo?modalidad=sucursal&sucursal=${branch.id}`}>Elegir sucursal</Link>
                  </div>
                </article>
              ))}
            </div>
            <section className="branches-page__map-panel" aria-label="Ubicación de la sucursal">
              <h2>{selectedBranch?.name ?? 'Ubicación en el mapa'}</h2>
              {selectedBranch?.latitude != null && selectedBranch.longitude != null ? (
                <ShipmentMap mode="location" latitude={selectedBranch.latitude} longitude={selectedBranch.longitude} accessibleName={`Ubicación de ${selectedBranch.name}`} />
              ) : <p>{selectedBranch ? 'Esta sucursal aún no tiene ubicación en el mapa.' : 'Seleccioná “Ver ubicación” en una sucursal para mostrarla en el mapa.'}</p>}
            </section>
          </div>
        )}
      </div>
    </main>
  )
}
