import { useRef, useState, type FormEvent } from 'react'
import { CircleAlert, LoaderCircle, Send } from 'lucide-react'
import { ClaimsApiError } from '../services/claimsApi'
import type { ClaimContext, ClaimFieldErrors, ClaimFormValues, ClaimType } from '../types/claim.types'

const emptyValues: ClaimFormValues = {
  type: '', packageNumber: '', description: '', contactName: '', contactEmail: '', contactPhone: '',
}

export function ClaimForm({ context, pending, onSubmit }: {
  context: ClaimContext
  pending: boolean
  onSubmit: (values: ClaimFormValues) => Promise<void>
}) {
  const [values, setValues] = useState(emptyValues)
  const [errors, setErrors] = useState<ClaimFieldErrors>({})
  const [message, setMessage] = useState('')
  const feedbackRef = useRef<HTMLDivElement>(null)

  function update(field: keyof ClaimFormValues, value: string) {
    setValues((current) => ({ ...current, [field]: value }))
    setErrors((current) => ({
      ...current,
      [field]: undefined,
      ...(field === 'contactEmail' || field === 'contactPhone' ? { contact: undefined } : {}),
    }))
    setMessage('')
  }

  function fieldError(field: keyof ClaimFormValues) {
    return errors[field] ? <small className="claim-form__field-error" id={`claim-${field}-error`}>{errors[field]}</small> : null
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (pending) return
    const nextErrors: ClaimFieldErrors = {}
    if (!context.types.some((type) => type.code === values.type)) nextErrors.type = 'Elegí un motivo.'
    if (values.description.trim().length < 20 || values.description.trim().length > 2000) {
      nextErrors.description = 'Describí el inconveniente con entre 20 y 2000 caracteres.'
    }
    if (values.contactName.trim().length < 2) nextErrors.contactName = 'Ingresá tu nombre (al menos 2 caracteres).'
    if (!values.contactEmail.trim() && !values.contactPhone.trim()) nextErrors.contact = 'Ingresá al menos un email o un teléfono para que podamos contactarte.'
    if (values.contactEmail.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.contactEmail.trim())) {
      nextErrors.contactEmail = 'Ingresá un email válido.'
    }
    const phone = values.contactPhone.trim()
    if (phone && (!/^\+?[0-9(][0-9\s\-()]{5,29}$/.test(phone) || phone.replace(/\D/g, '').length < 6)) {
      nextErrors.contactPhone = 'Usá al menos 6 dígitos. Podés incluir espacios, guiones, paréntesis y un + inicial.'
    }
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length) {
      setMessage('Revisá los campos indicados antes de enviar el reclamo.')
      requestAnimationFrame(() => feedbackRef.current?.focus())
      return
    }
    setMessage('')
    try {
      await onSubmit(values)
      setValues(emptyValues)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'No pudimos enviar el reclamo. Intentá nuevamente.')
      if (error instanceof ClaimsApiError) setErrors(error.fieldErrors)
      requestAnimationFrame(() => feedbackRef.current?.focus())
    }
  }

  return (
    <form className="claim-form" onSubmit={handleSubmit} noValidate aria-busy={pending}>
      <p className="claim-form__intro">Contanos qué pasó. Los campos con * son obligatorios.</p>
      {message && <div className="form-error" role="alert" tabIndex={-1} ref={feedbackRef}><CircleAlert size={18} aria-hidden="true" /><span>{message}</span></div>}
      <fieldset disabled={pending} className="claim-form__fields">
        <legend className="claim-form__legend">Datos del reclamo</legend>
        <div className="form-field">
          <label htmlFor="claim-packageNumber">¿Sobre qué querés reclamar?</label>
          <select className="form-control" id="claim-packageNumber" value={values.packageNumber} onChange={(event) => update('packageNumber', event.target.value)} aria-invalid={Boolean(errors.packageNumber)} aria-describedby={errors.packageNumber ? 'claim-packageNumber-error' : undefined}>
            <option value="">Todo el envío</option>
            {context.packages.map((item) => <option key={item.packageNumber} value={item.packageNumber}>{item.packageNumber} · {item.description}</option>)}
          </select>
          {fieldError('packageNumber')}
        </div>
        <div className="form-field">
          <label htmlFor="claim-type">Motivo del reclamo *</label>
          <select className="form-control" id="claim-type" value={values.type} onChange={(event) => update('type', event.target.value as ClaimType | '')} required aria-invalid={Boolean(errors.type)} aria-describedby={errors.type ? 'claim-type-error' : undefined}>
            <option value="">Seleccioná un motivo</option>
            {context.types.map((type) => <option key={type.code} value={type.code}>{type.description}</option>)}
          </select>
          {fieldError('type')}
        </div>
        <div className="form-field">
          <label htmlFor="claim-description">Descripción del inconveniente *</label>
          <textarea className="form-control" id="claim-description" value={values.description} onChange={(event) => update('description', event.target.value)} rows={4} minLength={20} maxLength={2000} required placeholder="Explicá qué ocurrió con tu envío o paquete." aria-invalid={Boolean(errors.description)} aria-describedby={`claim-description-help${errors.description ? ' claim-description-error' : ''}`} />
          <small id="claim-description-help">Entre 20 y 2000 caracteres · {values.description.trim().length}/2000. No incluyas datos personales: esta descripción será visible para quienes tengan el código de seguimiento.</small>
          {fieldError('description')}
        </div>
      </fieldset>
      <fieldset disabled={pending} className="claim-form__fields" aria-describedby={`claim-contact-help${errors.contact ? ' claim-contact-error' : ''}`}>
        <legend className="claim-form__legend">Cómo podemos contactarte</legend>
        <p id="claim-contact-help">Dejanos al menos un email o un teléfono. Tus datos de contacto no se muestran en el seguimiento público.</p>
        {errors.contact && <small className="claim-form__field-error" id="claim-contact-error">{errors.contact}</small>}
        <div className="form-field">
          <label htmlFor="claim-contactName">Nombre y apellido *</label>
          <input className="form-control" id="claim-contactName" autoComplete="name" value={values.contactName} onChange={(event) => update('contactName', event.target.value)} minLength={2} maxLength={150} required aria-invalid={Boolean(errors.contactName)} aria-describedby={errors.contactName ? 'claim-contactName-error' : undefined} />
          {fieldError('contactName')}
        </div>
        <div className="claim-form__contact-grid">
          <div className="form-field">
            <label htmlFor="claim-contactEmail">Email</label>
            <input className="form-control" id="claim-contactEmail" type="email" autoComplete="email" value={values.contactEmail} onChange={(event) => update('contactEmail', event.target.value)} aria-invalid={Boolean(errors.contactEmail || errors.contact)} aria-describedby={errors.contactEmail ? 'claim-contactEmail-error' : errors.contact ? 'claim-contact-error' : undefined} />
            {fieldError('contactEmail')}
          </div>
          <div className="form-field">
            <label htmlFor="claim-contactPhone">Teléfono</label>
            <input className="form-control" id="claim-contactPhone" type="tel" autoComplete="tel" maxLength={30} value={values.contactPhone} onChange={(event) => update('contactPhone', event.target.value)} aria-invalid={Boolean(errors.contactPhone || errors.contact)} aria-describedby={errors.contactPhone ? 'claim-contactPhone-error' : errors.contact ? 'claim-contact-error' : undefined} />
            {fieldError('contactPhone')}
          </div>
        </div>
      </fieldset>
      <button className="claim-button claim-button--primary" type="submit" disabled={pending}>
        {pending ? <LoaderCircle size={18} className="loading-icon" aria-hidden="true" /> : <Send size={18} aria-hidden="true" />}
        {pending ? 'Enviando reclamo…' : 'Enviar reclamo'}
      </button>
    </form>
  )
}
