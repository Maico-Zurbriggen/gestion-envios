import { useState, type FormEvent } from 'react'
import {
  Check,
  CheckCircle2,
  Clipboard,
  IdCard,
  Info,
  LoaderCircle,
  Mail,
  Phone,
  RotateCcw,
  Shield,
  UserPlus,
  UserRound,
} from 'lucide-react'
import { ASSIGNABLE_ROLES } from '../constants/roles'
import { useCreateUser } from '../hooks/useCreateUser'
import './CreateUserPage.css'

const INITIAL_FORM = {
  name: '',
  dni: '',
  email: '',
  phone: '',
  roleId: 2,
}

export function CreateUserPage() {
  const [form, setForm] = useState(INITIAL_FORM)
  const [passwordCopied, setPasswordCopied] = useState(false)
  const createUserMutation = useCreateUser()

  function updateField<Key extends keyof typeof form>(
    field: Key,
    value: (typeof form)[Key],
  ) {
    setForm((currentForm) => ({ ...currentForm, [field]: value }))
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    createUserMutation.mutate(
      {
        ...form,
        name: form.name.trim(),
        dni: form.dni.trim(),
        email: form.email.trim(),
        phone: form.phone.trim(),
      },
      {
        onSuccess: () => {
          setForm(INITIAL_FORM)
          setPasswordCopied(false)
        },
      },
    )
  }

  async function copyTemporaryPassword() {
    const password = createUserMutation.data?.temporaryPassword
    if (!password) return

    try {
      await navigator.clipboard.writeText(password)
      setPasswordCopied(true)
    } catch {
      setPasswordCopied(false)
    }
  }

  const errorMessage =
    createUserMutation.error instanceof Error
      ? createUserMutation.error.message
      : null

  if (createUserMutation.data) {
    const user = createUserMutation.data

    return (
      <main className="user-page">
        <section className="user-success" aria-labelledby="user-created-title">
          <span className="user-success__icon" aria-hidden="true">
            <CheckCircle2 size={30} />
          </span>
          <span className="eyebrow">Usuario registrado</span>
          <h1 id="user-created-title">Alta completada</h1>
          <p>
            {user.name} fue registrado con el rol {user.role.toLowerCase()}.
          </p>

          <dl className="user-summary">
            <div>
              <dt>DNI</dt>
              <dd>{user.dni}</dd>
            </div>
            <div>
              <dt>Email</dt>
              <dd>{user.email}</dd>
            </div>
            <div>
              <dt>Estado</dt>
              <dd>{user.status}</dd>
            </div>
          </dl>

          <div className="temporary-password">
            <div>
              <span>Contraseña temporal</span>
              <strong>{user.temporaryPassword}</strong>
            </div>
            <button
              type="button"
              onClick={copyTemporaryPassword}
              aria-label="Copiar contraseña temporal"
            >
              {passwordCopied ? (
                <Check size={19} aria-hidden="true" />
              ) : (
                <Clipboard size={19} aria-hidden="true" />
              )}
              {passwordCopied ? 'Copiada' : 'Copiar'}
            </button>
          </div>
          <p className="temporary-password__hint">
            Compartila por un canal seguro. El usuario deberá cambiarla en su
            primer ingreso.
          </p>

          <button
            className="create-another-user"
            type="button"
            onClick={() => createUserMutation.reset()}
          >
            <RotateCcw size={18} aria-hidden="true" />
            Registrar otro usuario
          </button>
        </section>
      </main>
    )
  }

  return (
    <main className="user-page">
      <header className="user-page__header">
        <span className="eyebrow">Administración de usuarios</span>
        <h1>Registrar nuevo usuario</h1>
        <p>
          Completá los datos del empleado. El sistema generará una contraseña
          temporal para su primer acceso.
        </p>
      </header>

      <section className="user-form-card" aria-labelledby="user-form-title">
        <div className="user-form-card__heading">
          <span aria-hidden="true">
            <UserPlus size={22} />
          </span>
          <div>
            <h2 id="user-form-title">Datos del empleado</h2>
            <p>Todos los campos son obligatorios.</p>
          </div>
        </div>

        <form className="user-form" onSubmit={handleSubmit}>
          <div className="user-form__grid">
            <div className="form-field user-form__full">
              <label htmlFor="employee-name">Nombre y apellido</label>
              <div className="input-control">
                <UserRound className="input-control__icon" size={19} aria-hidden="true" />
                <input
                  className="form-control form-control--with-icon"
                  id="employee-name"
                  type="text"
                  autoComplete="name"
                  placeholder="Ej. Carlos Gómez"
                  value={form.name}
                  onChange={(event) => updateField('name', event.target.value)}
                  minLength={2}
                  maxLength={100}
                  required
                  autoFocus
                />
              </div>
            </div>

            <div className="form-field">
              <label htmlFor="employee-dni">DNI</label>
              <div className="input-control">
                <IdCard className="input-control__icon" size={19} aria-hidden="true" />
                <input
                  className="form-control form-control--with-icon"
                  id="employee-dni"
                  type="text"
                  inputMode="numeric"
                  placeholder="35123456"
                  value={form.dni}
                  onChange={(event) =>
                    updateField('dni', event.target.value.replace(/\D/g, ''))
                  }
                  minLength={6}
                  maxLength={20}
                  pattern="[0-9]{6,20}"
                  required
                />
              </div>
            </div>

            <div className="form-field">
              <label htmlFor="employee-phone">Teléfono</label>
              <div className="input-control">
                <Phone className="input-control__icon" size={19} aria-hidden="true" />
                <input
                  className="form-control form-control--with-icon"
                  id="employee-phone"
                  type="tel"
                  autoComplete="tel"
                  placeholder="+543564123456"
                  value={form.phone}
                  onChange={(event) => updateField('phone', event.target.value)}
                  minLength={6}
                  maxLength={30}
                  pattern="\+?[0-9\s-]{6,30}"
                  required
                />
              </div>
            </div>

            <div className="form-field user-form__full">
              <label htmlFor="employee-email">Email</label>
              <div className="input-control">
                <Mail className="input-control__icon" size={19} aria-hidden="true" />
                <input
                  className="form-control form-control--with-icon"
                  id="employee-email"
                  type="email"
                  autoComplete="email"
                  placeholder="carlos.gomez@empresa.com"
                  value={form.email}
                  onChange={(event) => updateField('email', event.target.value)}
                  required
                />
              </div>
            </div>

            <div className="form-field user-form__full">
              <label htmlFor="employee-role">Rol</label>
              <div className="input-control">
                <Shield className="input-control__icon" size={19} aria-hidden="true" />
                <select
                  className="form-control form-control--with-icon"
                  id="employee-role"
                  value={form.roleId}
                  onChange={(event) =>
                    updateField('roleId', Number(event.target.value))
                  }
                  required
                >
                  {ASSIGNABLE_ROLES.map((role) => (
                    <option key={role.id} value={role.id}>
                      {role.label}
                    </option>
                  ))}
                </select>
              </div>
              <span className="role-source-note">
                <Info size={14} aria-hidden="true" />
                Roles disponibles definidos temporalmente en el frontend.
              </span>
            </div>
          </div>

          {errorMessage && (
            <p className="form-error" role="alert" aria-live="polite">
              <Info size={18} aria-hidden="true" />
              {errorMessage}
            </p>
          )}

          <div className="user-form__actions">
            <button
              className="user-submit"
              type="submit"
              disabled={createUserMutation.isPending}
            >
              {createUserMutation.isPending ? (
                <LoaderCircle
                  className="loading-icon"
                  size={18}
                  aria-hidden="true"
                />
              ) : (
                <UserPlus size={18} aria-hidden="true" />
              )}
              {createUserMutation.isPending ? 'Registrando…' : 'Registrar usuario'}
            </button>
          </div>
        </form>
      </section>
    </main>
  )
}
