import { useState, type FormEvent } from 'react'
import { Building2, CircleAlert, Globe, LoaderCircle, Mail, Phone, Save } from 'lucide-react'
import { Modal } from '../../../shared/components/Modal'
import type { EmailSettings } from '../types/email.types'

type SettingsValues = Omit<EmailSettings, 'updatedAt'>

interface EmailSettingsModalProps {
  open: boolean
  settings: EmailSettings
  pending: boolean
  error: string | null
  onClose: () => void
  onSave: (values: SettingsValues) => void
}

/** Datos de la empresa que firman todos los correos: marca, firma, contacto y aviso legal. */
export function EmailSettingsModal({ open, settings, ...props }: EmailSettingsModalProps) {
  return (
    <Modal
      open={open}
      onClose={props.onClose}
      icon={Building2}
      eyebrow="Correos a clientes"
      title="Datos de la empresa"
      description="Aparecen en el encabezado y el pie de todos los correos."
    >
      {/* Se vuelve a montar al abrir, con los datos guardados. */}
      {open ? <SettingsForm settings={settings} {...props} /> : null}
    </Modal>
  )
}

function SettingsForm({ settings, pending, error, onClose, onSave }: Omit<EmailSettingsModalProps, 'open'>) {
  const [values, setValues] = useState<SettingsValues>(() => ({
    brandName: settings.brandName,
    signature: settings.signature,
    contactPhone: settings.contactPhone,
    contactEmail: settings.contactEmail,
    website: settings.website,
    legalNotice: settings.legalNotice,
  }))

  function update(field: keyof SettingsValues, value: string) {
    setValues((current) => ({ ...current, [field]: value }))
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onSave(Object.fromEntries(Object.entries(values).map(([key, value]) => [key, value.trim()])) as SettingsValues)
  }

  return (
    <form className="email-settings-form" onSubmit={handleSubmit}>
      <div className="form-field email-settings-form__full">
        <label htmlFor="settings-brand">Nombre de la empresa</label>
        <div className="input-control">
          <Building2 className="input-control__icon" size={18} aria-hidden="true" />
          <input
            className="form-control form-control--with-icon"
            id="settings-brand"
            value={values.brandName}
            onChange={(event) => update('brandName', event.target.value)}
            maxLength={100}
            required
            autoFocus
          />
        </div>
      </div>
      <div className="form-field email-settings-form__full">
        <label htmlFor="settings-signature">Firma</label>
        <textarea
          className="form-control"
          id="settings-signature"
          rows={2}
          placeholder="Equipo de atención al cliente"
          value={values.signature}
          onChange={(event) => update('signature', event.target.value)}
          maxLength={300}
        />
      </div>
      <div className="form-field">
        <label htmlFor="settings-phone">Teléfono de contacto</label>
        <div className="input-control">
          <Phone className="input-control__icon" size={18} aria-hidden="true" />
          <input
            className="form-control form-control--with-icon"
            id="settings-phone"
            type="tel"
            value={values.contactPhone}
            onChange={(event) => update('contactPhone', event.target.value)}
            maxLength={40}
          />
        </div>
      </div>
      <div className="form-field">
        <label htmlFor="settings-email">Email de contacto</label>
        <div className="input-control">
          <Mail className="input-control__icon" size={18} aria-hidden="true" />
          <input
            className="form-control form-control--with-icon"
            id="settings-email"
            type="email"
            value={values.contactEmail}
            onChange={(event) => update('contactEmail', event.target.value)}
            maxLength={150}
          />
        </div>
      </div>
      <div className="form-field email-settings-form__full">
        <label htmlFor="settings-website">Sitio web</label>
        <div className="input-control">
          <Globe className="input-control__icon" size={18} aria-hidden="true" />
          <input
            className="form-control form-control--with-icon"
            id="settings-website"
            type="url"
            placeholder="https://"
            value={values.website}
            onChange={(event) => update('website', event.target.value)}
            maxLength={200}
          />
        </div>
      </div>
      <div className="form-field email-settings-form__full">
        <label htmlFor="settings-legal">Aviso legal</label>
        <textarea
          className="form-control"
          id="settings-legal"
          rows={3}
          value={values.legalNotice}
          onChange={(event) => update('legalNotice', event.target.value)}
          maxLength={600}
        />
      </div>
      {error ? (
        <p className="form-error email-settings-form__full" role="alert">
          <CircleAlert size={18} aria-hidden="true" />
          {error}
        </p>
      ) : null}
      <div className="email-settings-form__actions email-settings-form__full">
        <button className="btn btn--ghost" type="button" onClick={onClose}>
          Cancelar
        </button>
        <button className="btn btn--primary" type="submit" disabled={pending}>
          {pending ? <LoaderCircle className="loading-icon" size={17} aria-hidden="true" /> : <Save size={17} aria-hidden="true" />}
          {pending ? 'Guardando…' : 'Guardar datos'}
        </button>
      </div>
    </form>
  )
}
