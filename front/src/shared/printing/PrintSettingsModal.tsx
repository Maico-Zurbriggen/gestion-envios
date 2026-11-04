import { useId, useState } from 'react'
import { Check, CircleAlert, Info, Printer, Settings2 } from 'lucide-react'
import { Modal } from '../components/Modal'
import {
  MAX_COPIES,
  MIN_COPIES,
  PRINTER_PROFILES,
  clampCopies,
  findLabelSize,
  findPrinterProfile,
  getLabelLayout,
  type PrintSettings,
} from './printerProfiles'
import { SAMPLE_LABEL, printShipmentLabels } from './printLabels'
import './PrintSettingsModal.css'

interface PrintSettingsModalProps {
  settings: PrintSettings
  onSave: (settings: PrintSettings) => void
  onClose: () => void
}

const dateFormatter = new Intl.DateTimeFormat('es-AR', { dateStyle: 'short', timeStyle: 'short' })

/**
 * Configuración de impresión del puesto: perfil de impresora, tamaño de
 * etiqueta y copias. Se monta solo mientras está abierta, así el borrador
 * arranca siempre desde lo guardado.
 */
export function PrintSettingsModal({ settings, onSave, onClose }: PrintSettingsModalProps) {
  const ids = { profile: useId(), size: useId(), copies: useId(), copiesHint: useId() }
  const [profileId, setProfileId] = useState(settings.profileId)
  const [sizeId, setSizeId] = useState(settings.sizeId)
  const [copiesInput, setCopiesInput] = useState(String(settings.copies))
  const [error, setError] = useState('')
  const profile = findPrinterProfile(profileId)
  const size = findLabelSize(profile, sizeId)
  const layout = getLabelLayout(size)
  // Papel a escala dentro de un recuadro de 112 × 96 px.
  const previewScale = Math.min(112 / size.widthMm, 96 / size.heightMm)
  const draft: PrintSettings = { profileId: profile.id, sizeId: size.id, copies: clampCopies(copiesInput) }

  function changeProfile(value: string) {
    setProfileId(value)
    setSizeId(findPrinterProfile(value).sizes[0].id)
  }

  function printTest() {
    setError('')
    try {
      printShipmentLabels([{ ...SAMPLE_LABEL, date: dateFormatter.format(new Date()) }], { ...draft, copies: 1 })
    } catch {
      setError('No pudimos abrir la impresión de prueba. Revisá que el navegador permita imprimir desde esta página.')
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      icon={Settings2}
      eyebrow="Etiquetas"
      title="Configurar impresión"
      description="Se guarda en este navegador: cada puesto puede tener su propia impresora."
      footer={<>
        <button className="btn" type="button" onClick={printTest}><Printer size={18} aria-hidden="true" /> Imprimir prueba</button>
        <button className="btn btn--ghost" type="button" onClick={onClose}>Cancelar</button>
        <button className="btn btn--primary" type="button" onClick={() => { onSave(draft); onClose() }}><Check size={18} aria-hidden="true" /> Guardar configuración</button>
      </>}
    >
      <div className="print-settings">
        <div className="form-field">
          <label htmlFor={ids.profile}>Impresora</label>
          <select className="form-control" id={ids.profile} value={profile.id} onChange={(event) => changeProfile(event.target.value)}>
            {PRINTER_PROFILES.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        </div>
        <div className="print-settings__row">
          <div className="form-field">
            <label htmlFor={ids.size}>Tamaño de etiqueta</label>
            <select className="form-control" id={ids.size} value={size.id} onChange={(event) => setSizeId(event.target.value)} disabled={profile.sizes.length === 1}>
              {profile.sizes.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
          </div>
          <div className="form-field print-settings__copies">
            <label htmlFor={ids.copies}>Copias por paquete</label>
            <input
              className="form-control"
              id={ids.copies}
              type="number"
              inputMode="numeric"
              min={MIN_COPIES}
              max={MAX_COPIES}
              value={copiesInput}
              aria-describedby={ids.copiesHint}
              onChange={(event) => setCopiesInput(event.target.value)}
              onBlur={() => setCopiesInput(String(clampCopies(copiesInput)))}
            />
            <small id={ids.copiesHint}>Entre {MIN_COPIES} y {MAX_COPIES}.</small>
          </div>
        </div>

        <figure className="print-settings__preview">
          <div className="print-settings__paper" style={{ width: `${Math.round(size.widthMm * previewScale)}px`, height: `${Math.round(size.heightMm * previewScale)}px` }} aria-hidden="true">
            <span className="print-settings__bars" />
            {layout.variant === 'full' && <span className="print-settings__lines" />}
          </div>
          <figcaption>
            <strong>{size.widthMm} × {size.heightMm} mm</strong>
            <span>{layout.variant === 'compact'
              ? 'Etiqueta chica: código de barras, número de paquete y n/m.'
              : 'Etiqueta completa: marca, número, código de barras, seguimiento, destinatario, destino, peso y medidas.'}</span>
          </figcaption>
        </figure>

        <p className="print-settings__note">
          <Info size={18} aria-hidden="true" />
          <span>
            La impresora se elige en el diálogo del navegador. Configurá en su driver el mismo tamaño de papel ({size.widthMm} × {size.heightMm} mm) y, en el diálogo, dejá los márgenes en «Ninguno» y desactivá «Encabezados y pies de página». Si el tamaño no coincide, la etiqueta sale cortada o repartida en dos.
          </span>
        </p>
        {error && <p className="form-error" role="alert"><CircleAlert size={18} aria-hidden="true" />{error}</p>}
      </div>
    </Modal>
  )
}
