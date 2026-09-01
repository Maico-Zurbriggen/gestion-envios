import { useState, type FormEvent } from 'react'
import {
  ArrowLeft,
  Building2,
  CircleAlert,
  FileCheck2,
  House,
  LoaderCircle,
  LocateFixed,
  LogIn,
  MapPin,
  MapPinned,
  MousePointerClick,
  Moon,
  Package,
  PackageCheck,
  Plus,
  RefreshCw,
  Send,
  Sun,
  Trash2,
  UserRound,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAppSelector } from '../../../app/store'
import { selectIsAuthenticated } from '../../auth/redux/authSlice'
import { useTheme } from '../../../shared/hooks/useTheme'
import { useBranches } from '../hooks/useBranches'
import { useCreateShipment } from '../hooks/useCreateShipment'
import { useGeocodeDestination } from '../hooks/useGeocodeDestination'
import type { DeliveryType } from '../types/shipment.types'
import { ShipmentResult } from '../components/ShipmentResult'
import { ShipmentMap } from '../components/ShipmentMap'
import './CreateShipmentPage.css'

interface ShipmentForm {
  senderName: string
  senderDocument: string
  senderPhone: string
  senderEmail: string
  recipientName: string
  recipientPhone: string
  recipientEmail: string
  deliveryType: DeliveryType
  destinationProvince: string
  destinationCity: string
  destinationStreet: string
  destinationStreetNumber: string
  destinationLatitude: number | null
  destinationLongitude: number | null
  destinationBranchId: number | ''
  termsAccepted: boolean
}

interface PackageForm {
  key: string
  description: string
  weightKg: string
  lengthCm: string
  widthCm: string
  heightCm: string
  notes: string
}

const INITIAL_FORM: ShipmentForm = {
  senderName: '',
  senderDocument: '',
  senderPhone: '',
  senderEmail: '',
  recipientName: '',
  recipientPhone: '',
  recipientEmail: '',
  deliveryType: 'domicilio',
  destinationProvince: '',
  destinationCity: '',
  destinationStreet: '',
  destinationStreetNumber: '',
  destinationLatitude: null,
  destinationLongitude: null,
  destinationBranchId: '',
  termsAccepted: false,
}

function createEmptyPackage(): PackageForm {
  return {
    key: crypto.randomUUID(),
    description: '',
    weightKg: '',
    lengthCm: '',
    widthCm: '',
    heightCm: '',
    notes: '',
  }
}

export function CreateShipmentPage() {
  const [form, setForm] = useState(INITIAL_FORM)
  const [packages, setPackages] = useState<PackageForm[]>(() => [
    createEmptyPackage(),
  ])
  const [clientError, setClientError] = useState<string | null>(null)
  const isAuthenticated = useAppSelector(selectIsAuthenticated)
  const { theme, toggleTheme } = useTheme()
  const branchesQuery = useBranches()
  const createShipmentMutation = useCreateShipment()
  const geocodeMutation = useGeocodeDestination()
  const selectedBranch = branchesQuery.data?.find(
    (branch) => branch.id === form.destinationBranchId,
  )

  function updateForm<Key extends keyof ShipmentForm>(
    field: Key,
    value: ShipmentForm[Key],
  ) {
    const changesAddress =
      field === 'destinationProvince' ||
      field === 'destinationCity' ||
      field === 'destinationStreet' ||
      field === 'destinationStreetNumber'

    setForm((current) => ({
      ...current,
      [field]: value,
      ...(changesAddress
        ? { destinationLatitude: null, destinationLongitude: null }
        : {}),
    }))

    if (changesAddress) geocodeMutation.reset()
  }

  function locateDestination() {
    setClientError(null)
    geocodeMutation.mutate(
      {
        street: form.destinationStreet.trim(),
        streetNumber: form.destinationStreetNumber.trim(),
        city: form.destinationCity.trim(),
        province: form.destinationProvince.trim(),
      },
      {
        onSuccess: (result) => {
          setForm((current) => ({
            ...current,
            destinationLatitude: result.latitude,
            destinationLongitude: result.longitude,
          }))
        },
      },
    )
  }

  function clearDestinationLocation() {
    geocodeMutation.reset()
    setForm((current) => ({
      ...current,
      destinationLatitude: null,
      destinationLongitude: null,
    }))
  }

  function updatePackage(
    key: string,
    field: Exclude<keyof PackageForm, 'key'>,
    value: string,
  ) {
    setPackages((current) =>
      current.map((shipmentPackage) =>
        shipmentPackage.key === key
          ? { ...shipmentPackage, [field]: value }
          : shipmentPackage,
      ),
    )
  }

  function addPackage() {
    setPackages((current) => [...current, createEmptyPackage()])
  }

  function removePackage(key: string) {
    setPackages((current) =>
      current.length === 1
        ? current
        : current.filter((shipmentPackage) => shipmentPackage.key !== key),
    )
  }

  function resetForm() {
    setForm(INITIAL_FORM)
    setPackages([createEmptyPackage()])
    setClientError(null)
    createShipmentMutation.reset()
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setClientError(null)

    if (
      form.deliveryType === 'sucursal' &&
      form.destinationBranchId === ''
    ) {
      setClientError('Seleccioná la sucursal donde se retirará el envío.')
      return
    }

    const invalidPackageIndex = packages.findIndex(
      (shipmentPackage) =>
        Number(shipmentPackage.lengthCm) +
          Number(shipmentPackage.widthCm) +
          Number(shipmentPackage.heightCm) >
        250,
    )

    if (invalidPackageIndex >= 0) {
      setClientError(
        `La suma de las medidas del paquete ${invalidPackageIndex + 1} no puede superar los 250 cm.`,
      )
      return
    }

    createShipmentMutation.mutate({
      senderName: form.senderName.trim(),
      senderDocument: form.senderDocument.trim(),
      senderPhone: form.senderPhone.trim(),
      senderEmail: form.senderEmail.trim(),
      recipientName: form.recipientName.trim(),
      recipientPhone: form.recipientPhone.trim(),
      recipientEmail: form.recipientEmail.trim(),
      deliveryType: form.deliveryType,
      destinationProvince:
        form.deliveryType === 'domicilio'
          ? form.destinationProvince.trim()
          : null,
      destinationCity:
        form.deliveryType === 'domicilio' ? form.destinationCity.trim() : null,
      destinationAddress:
        form.deliveryType === 'domicilio'
          ? `${form.destinationStreet.trim()} ${form.destinationStreetNumber.trim()}`
          : null,
      destinationLatitude:
        form.deliveryType === 'domicilio'
          ? form.destinationLatitude
          : null,
      destinationLongitude:
        form.deliveryType === 'domicilio'
          ? form.destinationLongitude
          : null,
      destinationBranchId:
        form.deliveryType === 'sucursal'
          ? Number(form.destinationBranchId)
          : null,
      termsAccepted: form.termsAccepted,
      packages: packages.map((shipmentPackage) => ({
        description: shipmentPackage.description.trim(),
        weightKg: Number(shipmentPackage.weightKg),
        lengthCm: Number(shipmentPackage.lengthCm),
        widthCm: Number(shipmentPackage.widthCm),
        heightCm: Number(shipmentPackage.heightCm),
        notes: shipmentPackage.notes.trim() || null,
      })),
    })
  }

  if (createShipmentMutation.data) {
    return (
      <ShipmentResult
        shipment={createShipmentMutation.data}
        onCreateAnother={resetForm}
      />
    )
  }

  const requestError =
    createShipmentMutation.error instanceof Error
      ? createShipmentMutation.error.message
      : null

  return (
    <main className="shipment-page">
      <header className="shipment-public-header">
        <Link className="shipment-brand" to={isAuthenticated ? '/' : '/login'}>
          <span aria-hidden="true">
            <PackageCheck size={22} />
          </span>
          <strong>Gestión de envíos</strong>
        </Link>
        <div className="shipment-public-header__actions">
          <button type="button" onClick={toggleTheme} aria-label="Cambiar tema">
            {theme === 'light' ? (
              <Moon size={19} aria-hidden="true" />
            ) : (
              <Sun size={19} aria-hidden="true" />
            )}
          </button>
          <Link
            to={isAuthenticated ? '/' : '/login'}
            aria-label={isAuthenticated ? 'Volver al panel' : 'Iniciar sesión'}
          >
            {isAuthenticated ? (
              <ArrowLeft size={18} aria-hidden="true" />
            ) : (
              <LogIn size={18} aria-hidden="true" />
            )}
            <span>{isAuthenticated ? 'Volver al panel' : 'Ingresar'}</span>
          </Link>
        </div>
      </header>

      <div className="shipment-page__content">
        <header className="shipment-page__intro">
          <span className="eyebrow">Registro público</span>
          <h1>Prepará tu envío</h1>
          <p>
            Cargá los datos, imprimí la etiqueta y acercá cada paquete a una
            sucursal. No necesitás iniciar sesión.
          </p>
        </header>

        <form className="shipment-form" onSubmit={handleSubmit}>
          <fieldset className="shipment-form__section">
            <legend className="shipment-form__sr-only">Datos de contacto</legend>
            <div className="shipment-form__section-header">
              <span aria-hidden="true"><UserRound size={20} /></span>
              <span><strong>Datos de contacto</strong><small>Quién envía y quién recibe</small></span>
            </div>

            <section className="shipment-person-card" aria-labelledby="sender-section-title">
              <header>
                <span aria-hidden="true"><Send size={18} /></span>
                <div><h2 id="sender-section-title">Remitente</h2><p>Persona que entrega el paquete</p></div>
              </header>
              <div className="shipment-form__grid">
                <div className="form-field shipment-form__full">
                  <label htmlFor="sender-name">Nombre y apellido</label>
                  <input className="form-control" id="sender-name" value={form.senderName} onChange={(event) => updateForm('senderName', event.target.value)} minLength={2} maxLength={150} autoComplete="name" required />
                </div>
                <div className="form-field">
                  <label htmlFor="sender-document">DNI</label>
                  <input className="form-control" id="sender-document" value={form.senderDocument} onChange={(event) => updateForm('senderDocument', event.target.value.replace(/\D/g, ''))} inputMode="numeric" pattern="[0-9]{6,20}" minLength={6} maxLength={20} required />
                </div>
                <div className="form-field">
                  <label htmlFor="sender-phone">Teléfono</label>
                  <input className="form-control" id="sender-phone" value={form.senderPhone} onChange={(event) => updateForm('senderPhone', event.target.value)} type="tel" autoComplete="tel" minLength={6} maxLength={30} required />
                </div>
                <div className="form-field shipment-form__full">
                  <label htmlFor="sender-email">Email</label>
                  <input className="form-control" id="sender-email" value={form.senderEmail} onChange={(event) => updateForm('senderEmail', event.target.value)} type="email" autoComplete="email" required />
                </div>
              </div>
            </section>

            <section className="shipment-person-card" aria-labelledby="recipient-section-title">
              <header>
                <span aria-hidden="true"><UserRound size={18} /></span>
                <div><h2 id="recipient-section-title">Destinatario</h2><p>Persona que recibirá el envío</p></div>
              </header>
              <div className="shipment-form__grid">
                <div className="form-field shipment-form__full">
                  <label htmlFor="recipient-name">Nombre y apellido</label>
                  <input className="form-control" id="recipient-name" value={form.recipientName} onChange={(event) => updateForm('recipientName', event.target.value)} minLength={2} maxLength={150} required />
                </div>
                <div className="form-field">
                  <label htmlFor="recipient-phone">Teléfono</label>
                  <input className="form-control" id="recipient-phone" value={form.recipientPhone} onChange={(event) => updateForm('recipientPhone', event.target.value)} type="tel" minLength={6} maxLength={30} required />
                </div>
                <div className="form-field">
                  <label htmlFor="recipient-email">Email</label>
                  <input className="form-control" id="recipient-email" value={form.recipientEmail} onChange={(event) => updateForm('recipientEmail', event.target.value)} type="email" required />
                </div>
              </div>
            </section>
          </fieldset>

          <fieldset className="shipment-form__section">
            <legend className="shipment-form__sr-only">Destino</legend>
            <div className="shipment-form__section-header">
              <span aria-hidden="true"><MapPin size={20} /></span>
              <span><strong>Destino</strong><small>Cómo se entregará el envío</small></span>
            </div>

            <div className="delivery-options">
              <label className={form.deliveryType === 'domicilio' ? 'is-selected' : ''}>
                <input type="radio" name="delivery-type" value="domicilio" checked={form.deliveryType === 'domicilio'} onChange={() => updateForm('deliveryType', 'domicilio')} />
                <House size={21} aria-hidden="true" />
                <span><strong>A domicilio</strong><small>Entrega en una dirección particular</small></span>
              </label>
              <label className={form.deliveryType === 'sucursal' ? 'is-selected' : ''}>
                <input type="radio" name="delivery-type" value="sucursal" checked={form.deliveryType === 'sucursal'} onChange={() => updateForm('deliveryType', 'sucursal')} />
                <Building2 size={21} aria-hidden="true" />
                <span><strong>Retiro en sucursal</strong><small>El destinatario retira personalmente</small></span>
              </label>
            </div>

            {form.deliveryType === 'domicilio' ? (
              <div className="shipment-form__grid">
                <div className="form-field">
                  <label htmlFor="destination-province">Provincia</label>
                  <input className="form-control" id="destination-province" value={form.destinationProvince} onChange={(event) => updateForm('destinationProvince', event.target.value)} required />
                </div>
                <div className="form-field">
                  <label htmlFor="destination-city">Ciudad</label>
                  <input className="form-control" id="destination-city" value={form.destinationCity} onChange={(event) => updateForm('destinationCity', event.target.value)} required />
                </div>
                <div className="form-field">
                  <label htmlFor="destination-street">Calle</label>
                  <input className="form-control" id="destination-street" value={form.destinationStreet} onChange={(event) => updateForm('destinationStreet', event.target.value)} placeholder="Ej. San Martín" required />
                </div>
                <div className="form-field">
                  <label htmlFor="destination-street-number">Altura</label>
                  <input className="form-control" id="destination-street-number" value={form.destinationStreetNumber} onChange={(event) => updateForm('destinationStreetNumber', event.target.value)} inputMode="numeric" placeholder="Ej. 1234" required />
                </div>
                <div className="shipment-address-locator shipment-form__full">
                  <div>
                    <strong>¿Querés ubicar el domicilio?</strong>
                    <span>Buscaremos la dirección exacta y, si no aparece, centraremos la ciudad.</span>
                  </div>
                  <button
                    type="button"
                    onClick={locateDestination}
                    disabled={
                      geocodeMutation.isPending ||
                      !form.destinationProvince.trim() ||
                      !form.destinationCity.trim() ||
                      !form.destinationStreet.trim() ||
                      !form.destinationStreetNumber.trim()
                    }
                  >
                    {geocodeMutation.isPending ? (
                      <LoaderCircle className="loading-icon" size={17} aria-hidden="true" />
                    ) : (
                      <LocateFixed size={17} aria-hidden="true" />
                    )}
                    {geocodeMutation.isPending ? 'Buscando…' : 'Ubicar en el mapa'}
                  </button>
                </div>
                {geocodeMutation.isError && (
                  <p className="form-error shipment-form__full" role="alert">
                    <CircleAlert size={18} aria-hidden="true" />
                    {geocodeMutation.error.message}
                  </p>
                )}
                <section className="shipment-map-block shipment-form__full" aria-labelledby="home-map-title">
                  <header>
                    <div><MapPinned size={19} aria-hidden="true" /><span><strong id="home-map-title">Ubicación en el mapa</strong><small>Opcional: hacé clic para marcar el punto exacto.</small></span></div>
                    {form.destinationLatitude !== null && (
                      <button type="button" onClick={clearDestinationLocation}>Quitar ubicación</button>
                    )}
                  </header>
                  <ShipmentMap
                    mode="picker"
                    latitude={form.destinationLatitude}
                    longitude={form.destinationLongitude}
                    accessibleName="Mapa para seleccionar la ubicación de entrega"
                    onLocationChange={(latitude, longitude) => {
                      geocodeMutation.reset()
                      setForm((current) => ({ ...current, destinationLatitude: latitude, destinationLongitude: longitude }))
                    }}
                  />
                  <p className="shipment-map-message">
                    <MousePointerClick size={15} aria-hidden="true" />
                    {geocodeMutation.data
                      ? geocodeMutation.data.precision === 'address'
                        ? `Domicilio encontrado: ${geocodeMutation.data.label}`
                        : `No encontramos la calle exacta; centramos el mapa en ${geocodeMutation.data.label}.`
                      : form.destinationLatitude !== null
                        ? 'Ubicación seleccionada. Podés cambiarla haciendo clic en otro punto.'
                      : 'La dirección es suficiente; marcar el mapa ayuda a precisar la entrega.'}
                  </p>
                </section>
              </div>
            ) : (
              <div className="branch-destination">
                <div className="form-field">
                <label htmlFor="destination-branch">Sucursal de destino</label>
                <select className="form-control" id="destination-branch" value={form.destinationBranchId} onChange={(event) => updateForm('destinationBranchId', event.target.value ? Number(event.target.value) : '')} disabled={branchesQuery.isPending || branchesQuery.isError} required>
                  <option value="" disabled>
                    {branchesQuery.isPending ? 'Cargando sucursales…' : branchesQuery.isError ? 'No se pudieron cargar las sucursales' : 'Seleccioná una sucursal'}
                  </option>
                  {branchesQuery.data?.map((branch) => <option key={branch.id} value={branch.id}>{branch.name} — {branch.city}, {branch.province}</option>)}
                </select>
                {branchesQuery.isError ? (
                  <button className="shipment-inline-action" type="button" onClick={() => void branchesQuery.refetch()} disabled={branchesQuery.isFetching}>
                    {branchesQuery.isFetching ? <LoaderCircle className="loading-icon" size={15} /> : <RefreshCw size={15} aria-hidden="true" />}
                    Reintentar carga
                  </button>
                ) : selectedBranch ? (
                  <span className="shipment-field-note"><MapPin size={14} aria-hidden="true" />{selectedBranch.address}</span>
                ) : null}
                </div>

                {selectedBranch ? (
                  selectedBranch.latitude !== null && selectedBranch.longitude !== null ? (
                    <section className="shipment-map-block" aria-labelledby="branch-map-title">
                      <header><div><MapPinned size={19} aria-hidden="true" /><span><strong id="branch-map-title">{selectedBranch.name}</strong><small>{selectedBranch.address}, {selectedBranch.city}</small></span></div></header>
                      <ShipmentMap mode="location" latitude={selectedBranch.latitude} longitude={selectedBranch.longitude} accessibleName={`Ubicación de ${selectedBranch.name}`} />
                    </section>
                  ) : (
                    <div className="shipment-map-placeholder"><MapPinned size={25} aria-hidden="true" /><strong>Ubicación no disponible</strong><p>Esta sucursal todavía no tiene coordenadas para mostrarla en el mapa.</p></div>
                  )
                ) : (
                  <div className="shipment-map-placeholder"><MapPinned size={25} aria-hidden="true" /><strong>Seleccioná una sucursal</strong><p>Una vez seleccionada, su ubicación se mostrará en el mapa.</p></div>
                )}
              </div>
            )}
          </fieldset>

          <fieldset className="shipment-form__section">
            <legend className="shipment-form__sr-only">Paquetes</legend>
            <div className="shipment-form__section-header">
              <span aria-hidden="true"><Package size={20} /></span>
              <span><strong>Paquetes</strong><small>Detalle de cada bulto</small></span>
            </div>

            <p className="package-limits">Máximo por paquete: 25 kg, 150 cm por lado y 250 cm sumando sus tres medidas.</p>
            <div className="packages-list">
              {packages.map((shipmentPackage, index) => (
                <article className="package-form-card" key={shipmentPackage.key}>
                  <header>
                    <h2>Paquete {index + 1}</h2>
                    {packages.length > 1 && (
                      <button type="button" onClick={() => removePackage(shipmentPackage.key)} aria-label={`Eliminar paquete ${index + 1}`}><Trash2 size={18} aria-hidden="true" /> Eliminar</button>
                    )}
                  </header>
                  <div className="shipment-form__grid shipment-form__grid--package">
                    <div className="form-field shipment-form__full">
                      <label htmlFor={`package-description-${shipmentPackage.key}`}>Contenido declarado</label>
                      <input className="form-control" id={`package-description-${shipmentPackage.key}`} value={shipmentPackage.description} onChange={(event) => updatePackage(shipmentPackage.key, 'description', event.target.value)} placeholder="Ej. Ropa y calzado" minLength={2} maxLength={255} required />
                    </div>
                    <div className="form-field">
                      <label htmlFor={`package-weight-${shipmentPackage.key}`}>Peso (kg)</label>
                      <input className="form-control" id={`package-weight-${shipmentPackage.key}`} value={shipmentPackage.weightKg} onChange={(event) => updatePackage(shipmentPackage.key, 'weightKg', event.target.value)} type="number" inputMode="decimal" min="0.01" max="25" step="0.01" required />
                    </div>
                    <div className="package-dimensions">
                      <div className="form-field"><label htmlFor={`package-length-${shipmentPackage.key}`}>Largo (cm)</label><input className="form-control" id={`package-length-${shipmentPackage.key}`} value={shipmentPackage.lengthCm} onChange={(event) => updatePackage(shipmentPackage.key, 'lengthCm', event.target.value)} type="number" inputMode="decimal" min="0.01" max="150" step="0.01" required /></div>
                      <div className="form-field"><label htmlFor={`package-width-${shipmentPackage.key}`}>Ancho (cm)</label><input className="form-control" id={`package-width-${shipmentPackage.key}`} value={shipmentPackage.widthCm} onChange={(event) => updatePackage(shipmentPackage.key, 'widthCm', event.target.value)} type="number" inputMode="decimal" min="0.01" max="150" step="0.01" required /></div>
                      <div className="form-field"><label htmlFor={`package-height-${shipmentPackage.key}`}>Alto (cm)</label><input className="form-control" id={`package-height-${shipmentPackage.key}`} value={shipmentPackage.heightCm} onChange={(event) => updatePackage(shipmentPackage.key, 'heightCm', event.target.value)} type="number" inputMode="decimal" min="0.01" max="150" step="0.01" required /></div>
                    </div>
                    <div className="form-field shipment-form__full">
                      <label htmlFor={`package-notes-${shipmentPackage.key}`}>Observaciones <small>(opcional)</small></label>
                      <textarea className="form-control shipment-textarea" id={`package-notes-${shipmentPackage.key}`} value={shipmentPackage.notes} onChange={(event) => updatePackage(shipmentPackage.key, 'notes', event.target.value)} maxLength={500} rows={3} placeholder="Indicaciones para la manipulación del paquete" />
                    </div>
                  </div>
                </article>
              ))}
            </div>
            <button className="add-package-button" type="button" onClick={addPackage}><Plus size={18} aria-hidden="true" />Agregar otro paquete</button>
          </fieldset>

          <section className="shipment-form__confirmation" aria-labelledby="shipment-confirmation-title">
            <FileCheck2 size={22} aria-hidden="true" />
            <div>
              <h2 id="shipment-confirmation-title">Confirmación</h2>
              <label className="terms-check">
                <input type="checkbox" checked={form.termsAccepted} onChange={(event) => updateForm('termsAccepted', event.target.checked)} required />
                <span>Acepto los términos del servicio y declaro que los datos y el contenido informado son correctos.</span>
              </label>
            </div>
          </section>

          {(clientError || requestError) && (
            <p className="form-error" role="alert" aria-live="polite"><CircleAlert size={18} aria-hidden="true" />{clientError || requestError}</p>
          )}

          <footer className="shipment-form__submit-row">
            <div><strong>Último paso</strong><span>Al registrar se generarán las etiquetas imprimibles.</span></div>
            <button type="submit" disabled={createShipmentMutation.isPending}>
              {createShipmentMutation.isPending ? <LoaderCircle className="loading-icon" size={19} aria-hidden="true" /> : <Send size={19} aria-hidden="true" />}
              {createShipmentMutation.isPending ? 'Registrando…' : 'Registrar y generar planilla'}
            </button>
          </footer>
        </form>
      </div>
    </main>
  )
}
