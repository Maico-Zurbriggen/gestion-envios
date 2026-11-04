import { useRef, useState } from 'react'
import { CircleAlert, Printer, Settings2 } from 'lucide-react'
import { PrintSettingsModal } from './PrintSettingsModal'
import { findPrinterProfile, resolveLabelSize } from './printerProfiles'
import { printShipmentLabels } from './printLabels'
import type { ShipmentLabelData } from './shipmentLabels'
import { usePrintSettings } from './usePrintSettings'
import './PrintSettingsModal.css'

interface PrintLabelsButtonProps {
  labels: readonly ShipmentLabelData[]
  /** Texto del botón principal. */
  label?: string
  className?: string
  settingsClassName?: string
  disabled?: boolean
}

/**
 * "Imprimir etiquetas" con la impresora configurada en este puesto, más el
 * acceso a "Configurar impresión". Devuelve un fragmento para sumarse a la
 * fila de acciones de cada pantalla sin cambiar su maquetación.
 */
export function PrintLabelsButton({ labels, label = 'Imprimir etiquetas', className = 'ops-button', settingsClassName = className, disabled = false }: PrintLabelsButtonProps) {
  const [settings, saveSettings] = usePrintSettings()
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [error, setError] = useState('')
  const settingsButtonRef = useRef<HTMLButtonElement>(null)
  const size = resolveLabelSize(settings)
  const summary = `${findPrinterProfile(settings.profileId).name} · ${size.name} · ${settings.copies} ${settings.copies === 1 ? 'copia' : 'copias'} por paquete`

  function print() {
    setError('')
    try {
      printShipmentLabels(labels, settings)
    } catch {
      setError('No pudimos abrir la impresión. Revisá que el navegador permita imprimir y volvé a intentarlo.')
    }
  }

  function closeSettings() {
    setSettingsOpen(false)
    requestAnimationFrame(() => settingsButtonRef.current?.focus())
  }

  return <>
    <button className={className} type="button" disabled={disabled || labels.length === 0} onClick={print} title={summary}>
      <Printer size={18} aria-hidden="true" /> {label}
    </button>
    <button ref={settingsButtonRef} className={settingsClassName} type="button" aria-haspopup="dialog" onClick={() => setSettingsOpen(true)} title={summary}>
      <Settings2 size={18} aria-hidden="true" /> Configurar impresión
    </button>
    {settingsOpen && <PrintSettingsModal settings={settings} onSave={saveSettings} onClose={closeSettings} />}
    {error && <p className="form-error print-labels__error" role="alert"><CircleAlert size={18} aria-hidden="true" />{error}</p>}
  </>
}
