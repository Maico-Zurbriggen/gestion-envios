import { useEffect, useRef, useState, type FormEvent } from 'react'
import {
  Building2,
  CircleAlert,
  Eye,
  History,
  LoaderCircle,
  Mail,
  Mails,
  Monitor,
  RefreshCw,
  RotateCcw,
  Save,
  Send,
  Smartphone,
  Sparkles,
  Undo2,
} from 'lucide-react'
import { useAppSelector } from '../../../app/store'
import { Modal } from '../../../shared/components/Modal'
import { PageHeader } from '../../../shared/components/PageHeader'
import { showToast } from '../../../shared/services/toast'
import { selectCurrentUser } from '../../auth/redux/authSlice'
import { EmailSettingsModal } from '../components/EmailSettingsModal'
import { useEmailPreview, useEmailTemplateMutations, useEmailTemplates } from '../hooks/useEmailTemplates'
import type { EmailTemplate, TemplateTexts } from '../types/email.types'
import './EmailTemplatesPage.css'

type Field = keyof TemplateTexts

const FIELDS: ReadonlyArray<{ id: Field; label: string; hint: string; multiline?: boolean; maxLength: number; optional?: boolean }> = [
  { id: 'subject', label: 'Asunto', hint: 'Lo primero que ve el cliente en su bandeja de entrada.', maxLength: 200 },
  { id: 'title', label: 'Título', hint: 'Encabezado grande del correo.', maxLength: 150 },
  { id: 'message', label: 'Mensaje', hint: 'Dejá una línea en blanco para separar párrafos.', multiline: true, maxLength: 2000 },
  { id: 'buttonText', label: 'Texto del botón', hint: 'El botón lleva al seguimiento del envío.', maxLength: 60 },
  { id: 'footer', label: 'Nota final', hint: 'Opcional. Aparece debajo del botón, en letra más chica.', multiline: true, maxLength: 600, optional: true },
]

const dateTimeFormatter = new Intl.DateTimeFormat('es-AR', { dateStyle: 'short', timeStyle: 'short' })

function textsOf(template: EmailTemplate): TemplateTexts {
  return {
    subject: template.subject,
    title: template.title,
    message: template.message,
    buttonText: template.buttonText,
    footer: template.footer,
  }
}

function withoutKey(drafts: Record<string, TemplateTexts>, key: string) {
  const next = { ...drafts }
  delete next[key]
  return next
}

function sameTexts(a: TemplateTexts, b: TemplateTexts) {
  return FIELDS.every(({ id }) => a[id] === b[id])
}

/** Devuelve el valor recién cuando dejó de cambiar durante `delay` ms. */
function useDebounced<T>(value: T, delay: number) {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay)
    return () => window.clearTimeout(timer)
  }, [value, delay])
  return debounced
}

export function EmailTemplatesPage() {
  const templatesQuery = useEmailTemplates()
  const templates = templatesQuery.data?.templates ?? []
  const settings = templatesQuery.data?.settings
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [drafts, setDrafts] = useState<Record<string, TemplateTexts>>({})
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [confirmReset, setConfirmReset] = useState(false)
  const [testOpen, setTestOpen] = useState(false)
  const [device, setDevice] = useState<'desktop' | 'mobile'>('desktop')

  const selected = templates.find((template) => template.key === selectedKey) ?? templates[0] ?? null
  const saved = selected ? textsOf(selected) : null
  const draft = selected ? (drafts[selected.key] ?? saved) : null
  const dirty = Boolean(draft && saved && !sameTexts(draft, saved))
  const differsFromFactory = Boolean(selected && draft && !sameTexts(draft, selected.factory))

  const debouncedDraft = useDebounced(draft, 450)
  const preview = useEmailPreview(selected?.key ?? null, debouncedDraft)
  const { save, reset, saveSettings, sendTest } = useEmailTemplateMutations()

  const fieldRefs = useRef<Partial<Record<Field, HTMLInputElement | HTMLTextAreaElement | null>>>({})
  const lastField = useRef<Field>('message')

  function setField(field: Field, value: string) {
    if (!selected || !draft) return
    setDrafts((current) => ({ ...current, [selected.key]: { ...draft, [field]: value } }))
  }

  function insertVariable(name: string) {
    if (!draft) return
    const field = lastField.current
    const element = fieldRefs.current[field]
    const token = `{${name}}`
    const value = draft[field]
    const start = element?.selectionStart ?? value.length
    const end = element?.selectionEnd ?? value.length
    setField(field, value.slice(0, start) + token + value.slice(end))
    window.requestAnimationFrame(() => {
      element?.focus()
      element?.setSelectionRange(start + token.length, start + token.length)
    })
  }

  function discard() {
    if (!selected) return
    setDrafts((current) => withoutKey(current, selected.key))
    save.reset()
  }

  function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selected || !draft) return
    save.mutate(
      { key: selected.key, texts: draft },
      {
        onSuccess: (template) => {
          setDrafts((current) => withoutKey(current, template.key))
          showToast(`Se guardó la plantilla «${template.name}». Los próximos correos ya salen así.`)
        },
      },
    )
  }

  function handleReset() {
    if (!selected) return
    reset.mutate(selected.key, {
      onSuccess: (template) => {
        setDrafts((current) => withoutKey(current, template.key))
        setConfirmReset(false)
        showToast(`«${template.name}» volvió a los textos de fábrica.`)
      },
      onError: (error) => showToast(error.message, 'error'),
    })
  }

  if (templatesQuery.isPending) {
    return (
      <main className="email-templates-page" aria-busy="true">
        <PageHeader icon={Mails} title="Correos a clientes" description="Cargando las plantillas…" />
        <div className="email-layout">
          <span className="skeleton email-skeleton" />
          <span className="skeleton email-skeleton" />
        </div>
      </main>
    )
  }

  if (templatesQuery.isError || !selected || !draft) {
    return (
      <main className="email-templates-page">
        <PageHeader icon={Mails} title="Correos a clientes" />
        <div className="list-card list-empty" role="alert">
          <CircleAlert size={30} aria-hidden="true" />
          <strong>No pudimos cargar las plantillas</strong>
          <p>{templatesQuery.error?.message ?? 'Intentá nuevamente en unos segundos.'}</p>
          <button className="btn" type="button" onClick={() => void templatesQuery.refetch()}>
            <RefreshCw size={16} aria-hidden="true" />
            Reintentar
          </button>
        </div>
      </main>
    )
  }

  return (
    <main className="email-templates-page">
      <PageHeader
        icon={Mails}
        eyebrow="Comunicación"
        title="Correos a clientes"
        description="Personalizá lo que reciben remitentes y destinatarios. Probá los cambios con datos de ejemplo antes de guardarlos."
        actions={
          <button className="btn" type="button" onClick={() => setSettingsOpen(true)}>
            <Building2 size={18} aria-hidden="true" />
            Datos de la empresa
          </button>
        }
      />

      <div className="email-template-picker" role="tablist" aria-label="Plantillas de correo">
        {templates.map((template) => {
          const pending = Boolean(drafts[template.key] && !sameTexts(drafts[template.key], textsOf(template)))
          const active = template.key === selected.key
          return (
            <button
              key={template.key}
              className={`email-template-card ${active ? 'is-active' : ''}`}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => setSelectedKey(template.key)}
            >
              <span className="email-template-card__icon" aria-hidden="true">
                <Mail size={18} />
              </span>
              <span className="email-template-card__body">
                <strong>{template.name}</strong>
                <small>{template.description}</small>
                <span className="email-template-card__badges">
                  <span className={`badge ${template.customized ? '' : 'badge--muted'}`}>
                    {template.customized ? 'Personalizada' : 'De fábrica'}
                  </span>
                  {pending ? <span className="badge badge--warning">Sin guardar</span> : null}
                </span>
              </span>
            </button>
          )
        })}
      </div>

      <div className="email-layout">
        <form className="surface-card email-editor" onSubmit={handleSave} aria-labelledby="email-editor-title">
          <header className="email-editor__header">
            <div>
              <h2 id="email-editor-title">{selected.name}</h2>
              <p>
                {selected.customized && selected.updatedAt
                  ? `Última modificación: ${dateTimeFormatter.format(new Date(selected.updatedAt))}`
                  : 'Usando los textos de fábrica.'}
              </p>
            </div>
          </header>

          <div className="email-variables">
            <p>
              <Sparkles size={15} aria-hidden="true" />
              Variables: tocá una para insertarla donde está el cursor.
            </p>
            <div className="email-variables__chips">
              {selected.variables.map((variable) => (
                <button
                  key={variable.name}
                  className="email-chip"
                  type="button"
                  title={variable.description}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => insertVariable(variable.name)}
                >
                  {`{${variable.name}}`}
                  <span className="visually-hidden">: {variable.description}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="email-editor__fields">
            {FIELDS.map((field) => {
              const id = `email-${field.id}`
              const common = {
                id,
                className: 'form-control',
                value: draft[field.id],
                maxLength: field.maxLength,
                required: !field.optional,
                onFocus: () => {
                  lastField.current = field.id
                },
                'aria-describedby': `${id}-hint`,
              }
              return (
                <div className="form-field" key={field.id}>
                  <label htmlFor={id}>
                    {field.label}
                    <span className="email-counter" aria-hidden="true">
                      {draft[field.id].length}/{field.maxLength}
                    </span>
                  </label>
                  {field.multiline ? (
                    <textarea
                      {...common}
                      ref={(element) => {
                        fieldRefs.current[field.id] = element
                      }}
                      rows={field.id === 'message' ? 7 : 3}
                      onChange={(event) => setField(field.id, event.target.value)}
                    />
                  ) : (
                    <input
                      {...common}
                      ref={(element) => {
                        fieldRefs.current[field.id] = element
                      }}
                      onChange={(event) => setField(field.id, event.target.value)}
                    />
                  )}
                  <span className="email-field-hint" id={`${id}-hint`}>
                    {field.hint}
                  </span>
                </div>
              )
            })}
          </div>

          {save.error ? (
            <p className="form-error" role="alert">
              <CircleAlert size={18} aria-hidden="true" />
              {save.error.message}
            </p>
          ) : null}

          <footer className="email-editor__actions">
            <button
              className="btn btn--ghost"
              type="button"
              disabled={!selected.customized && !differsFromFactory}
              onClick={() => setConfirmReset(true)}
            >
              <History size={17} aria-hidden="true" />
              Restablecer de fábrica
            </button>
            <div className="email-editor__save">
              <button className="btn" type="button" disabled={!dirty} onClick={discard}>
                <Undo2 size={17} aria-hidden="true" />
                Descartar
              </button>
              <button className="btn btn--primary" type="submit" disabled={!dirty || save.isPending}>
                {save.isPending ? <LoaderCircle className="loading-icon" size={17} aria-hidden="true" /> : <Save size={17} aria-hidden="true" />}
                {save.isPending ? 'Guardando…' : 'Guardar plantilla'}
              </button>
            </div>
          </footer>
        </form>

        <section className="surface-card email-preview" aria-labelledby="email-preview-title">
          <header className="email-preview__header">
            <h2 id="email-preview-title">
              <Eye size={18} aria-hidden="true" />
              Vista previa
              {preview.isFetching ? <LoaderCircle className="loading-icon" size={15} aria-label="Actualizando" /> : null}
            </h2>
            <div className="segmented" role="group" aria-label="Tamaño de pantalla">
              <button type="button" aria-pressed={device === 'desktop'} onClick={() => setDevice('desktop')}>
                <Monitor size={15} aria-hidden="true" />
                <span>Escritorio</span>
              </button>
              <button type="button" aria-pressed={device === 'mobile'} onClick={() => setDevice('mobile')}>
                <Smartphone size={15} aria-hidden="true" />
                <span>Celular</span>
              </button>
            </div>
          </header>

          <dl className="email-preview__envelope">
            <div>
              <dt>De</dt>
              <dd>{settings?.brandName || 'Gestión de Envíos'}</dd>
            </div>
            <div>
              <dt>Asunto</dt>
              <dd>{preview.data?.subject ?? '…'}</dd>
            </div>
          </dl>

          {preview.error ? (
            <p className="form-error email-preview__error" role="alert">
              <CircleAlert size={18} aria-hidden="true" />
              {preview.error.message}
            </p>
          ) : null}

          <div className={`email-preview__frame email-preview__frame--${device}`}>
            {preview.data ? (
              <iframe title="Vista previa del correo" sandbox="" srcDoc={preview.data.html} />
            ) : (
              <span className="skeleton email-skeleton" />
            )}
          </div>

          <footer className="email-preview__footer">
            <p>Se muestra con datos de ejemplo. El envío real usa los datos de cada envío.</p>
            <button className="btn" type="button" onClick={() => setTestOpen(true)}>
              <Send size={17} aria-hidden="true" />
              Enviar prueba
            </button>
          </footer>
        </section>
      </div>

      <Modal
        open={confirmReset}
        onClose={() => setConfirmReset(false)}
        size="narrow"
        icon={RotateCcw}
        eyebrow="Confirmar acción"
        title="Restablecer de fábrica"
        description={`«${selected.name}» vuelve a los textos originales. Se pierden los cambios guardados y los que no guardaste.`}
        footer={
          <>
            <button className="btn btn--ghost" type="button" onClick={() => setConfirmReset(false)}>
              Cancelar
            </button>
            <button className="btn btn--primary" type="button" disabled={reset.isPending} onClick={handleReset}>
              {reset.isPending ? <LoaderCircle className="loading-icon" size={17} aria-hidden="true" /> : <RotateCcw size={17} aria-hidden="true" />}
              Restablecer
            </button>
          </>
        }
      >
        <p className="email-reset-preview">
          <strong>Asunto de fábrica:</strong> {selected.factory.subject}
        </p>
      </Modal>

      <SendTestModal
        open={testOpen}
        pending={sendTest.isPending}
        error={sendTest.error?.message ?? null}
        onClose={() => {
          setTestOpen(false)
          sendTest.reset()
        }}
        onSend={(email) =>
          sendTest.mutate(
            { key: selected.key, texts: draft, email },
            {
              onSuccess: ({ to }) => {
                setTestOpen(false)
                showToast(`Enviamos un correo de prueba a ${to}.`)
              },
            },
          )
        }
      />

      {settings ? (
        <EmailSettingsModal
          open={settingsOpen}
          settings={settings}
          pending={saveSettings.isPending}
          error={saveSettings.error?.message ?? null}
          onClose={() => {
            setSettingsOpen(false)
            saveSettings.reset()
          }}
          onSave={(values) =>
            saveSettings.mutate(values, {
              onSuccess: () => {
                setSettingsOpen(false)
                showToast('Se guardaron los datos de la empresa. Ya aparecen en todos los correos.')
              },
            })
          }
        />
      ) : null}
    </main>
  )
}

interface SendTestModalProps {
  open: boolean
  pending: boolean
  error: string | null
  onClose: () => void
  onSend: (email: string) => void
}

function SendTestModal({ open, pending, error, onClose, onSend }: SendTestModalProps) {
  const user = useAppSelector(selectCurrentUser)
  return (
    <Modal
      open={open}
      onClose={onClose}
      size="narrow"
      icon={Send}
      eyebrow="Correo de prueba"
      title="Enviar una prueba"
      description="Llega con el asunto marcado como [Prueba] y los textos que estás editando, aunque no los hayas guardado."
    >
      <form
        className="email-test-form"
        onSubmit={(event) => {
          event.preventDefault()
          const email = new FormData(event.currentTarget).get('email')
          if (typeof email === 'string' && email.trim()) onSend(email.trim())
        }}
      >
        <div className="form-field">
          <label htmlFor="email-test-address">Enviar a</label>
          <div className="input-control">
            <Mail className="input-control__icon" size={18} aria-hidden="true" />
            <input
              className="form-control form-control--with-icon"
              id="email-test-address"
              name="email"
              type="email"
              defaultValue={user?.email ?? ''}
              placeholder="nombre@empresa.com"
              required
              autoFocus
            />
          </div>
        </div>
        {error ? (
          <p className="form-error" role="alert">
            <CircleAlert size={18} aria-hidden="true" />
            {error}
          </p>
        ) : null}
        <div className="email-test-form__actions">
          <button className="btn btn--ghost" type="button" onClick={onClose}>
            Cancelar
          </button>
          <button className="btn btn--primary" type="submit" disabled={pending}>
            {pending ? <LoaderCircle className="loading-icon" size={17} aria-hidden="true" /> : <Send size={17} aria-hidden="true" />}
            {pending ? 'Enviando…' : 'Enviar prueba'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
