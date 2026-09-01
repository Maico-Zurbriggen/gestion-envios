import { useState, type FormEvent } from 'react'
import {
  ArrowLeft,
  Check,
  Circle,
  CircleAlert,
  Eye,
  EyeOff,
  KeyRound,
  LoaderCircle,
  LockKeyhole,
  Save,
} from 'lucide-react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAppDispatch, useAppSelector } from '../../../app/store'
import { useChangePassword } from '../hooks/useChangePassword'
import {
  clearCredentials,
  selectAuthToken,
  selectIsAuthenticated,
  selectPasswordChangeChallenge,
} from '../redux/authSlice'
import './LoginPage.css'
import './ChangePasswordPage.css'

type PasswordFieldName = 'current' | 'new' | 'confirmation'

interface PasswordFieldProps {
  id: string
  label: string
  value: string
  autoComplete: string
  placeholder: string
  visible: boolean
  describedBy?: string
  onChange: (value: string) => void
  onToggleVisibility: () => void
}

function PasswordField({
  id,
  label,
  value,
  autoComplete,
  placeholder,
  visible,
  describedBy,
  onChange,
  onToggleVisibility,
}: PasswordFieldProps) {
  return (
    <div className="form-field">
      <label htmlFor={id}>{label}</label>
      <div className="input-control">
        <LockKeyhole
          className="input-control__icon"
          size={19}
          aria-hidden="true"
        />
        <input
          className="form-control form-control--with-icon form-control--with-action"
          id={id}
          name={id}
          type={visible ? 'text' : 'password'}
          autoComplete={autoComplete}
          placeholder={placeholder}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          aria-describedby={describedBy}
          required
        />
        <button
          className="password-toggle"
          type="button"
          onClick={onToggleVisibility}
          aria-label={visible ? `Ocultar ${label}` : `Mostrar ${label}`}
          aria-pressed={visible}
        >
          {visible ? (
            <EyeOff size={19} aria-hidden="true" />
          ) : (
            <Eye size={19} aria-hidden="true" />
          )}
        </button>
      </div>
    </div>
  )
}

export function ChangePasswordPage() {
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [passwordConfirmation, setPasswordConfirmation] = useState('')
  const [visibleField, setVisibleField] = useState<PasswordFieldName | null>(null)
  const [validationError, setValidationError] = useState<string | null>(null)
  const isAuthenticated = useAppSelector(selectIsAuthenticated)
  const authToken = useAppSelector(selectAuthToken)
  const passwordChangeChallenge = useAppSelector(selectPasswordChangeChallenge)
  const changePasswordMutation = useChangePassword()
  const dispatch = useAppDispatch()
  const navigate = useNavigate()

  if (!authToken && !passwordChangeChallenge?.token) {
    return <Navigate to="/login" replace />
  }

  const passwordRules = [
    { label: 'Al menos 10 caracteres', valid: newPassword.length >= 10 },
    { label: 'Una letra mayúscula', valid: /[A-Z]/.test(newPassword) },
    { label: 'Una letra minúscula', valid: /[a-z]/.test(newPassword) },
    { label: 'Un número', valid: /[0-9]/.test(newPassword) },
    { label: 'Un símbolo: ! @ # $ % & *', valid: /[!@#$%&*]/.test(newPassword) },
  ]

  function toggleVisibility(field: PasswordFieldName) {
    setVisibleField((currentField) => (currentField === field ? null : field))
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setValidationError(null)

    if (!passwordRules.every((rule) => rule.valid)) {
      setValidationError('La nueva contraseña no cumple todos los requisitos.')
      return
    }

    if (newPassword !== passwordConfirmation) {
      setValidationError('La confirmación no coincide con la nueva contraseña.')
      return
    }

    changePasswordMutation.mutate(
      { currentPassword, newPassword, passwordConfirmation },
      { onSuccess: () => navigate('/', { replace: true }) },
    )
  }

  function handleCancel() {
    if (!isAuthenticated) dispatch(clearCredentials())
    navigate(isAuthenticated ? '/' : '/login', { replace: true })
  }

  const errorMessage =
    validationError ??
    (changePasswordMutation.error instanceof Error
      ? changePasswordMutation.error.message
      : null)

  return (
    <main className="password-change-page">
      <section className="password-change-card" aria-labelledby="change-title">
        <header className="password-change-header">
          <span className="password-change-header__icon" aria-hidden="true">
            <KeyRound size={25} />
          </span>
          <div>
            <span className="eyebrow">Seguridad de la cuenta</span>
            <h1 id="change-title">Cambiar contraseña</h1>
            <p>Definí una clave segura que no hayas utilizado anteriormente.</p>
          </div>
        </header>

        <form className="password-change-form" onSubmit={handleSubmit}>
          <PasswordField
            id="current-password"
            label="Contraseña actual"
            value={currentPassword}
            autoComplete="current-password"
            placeholder="Ingresá tu contraseña actual"
            visible={visibleField === 'current'}
            onChange={setCurrentPassword}
            onToggleVisibility={() => toggleVisibility('current')}
          />

          <PasswordField
            id="new-password"
            label="Nueva contraseña"
            value={newPassword}
            autoComplete="new-password"
            placeholder="Creá una contraseña segura"
            visible={visibleField === 'new'}
            describedBy="password-requirements"
            onChange={(value) => {
              setNewPassword(value)
              setValidationError(null)
            }}
            onToggleVisibility={() => toggleVisibility('new')}
          />

          <ul className="password-requirements" id="password-requirements">
            {passwordRules.map((rule) => (
              <li className={rule.valid ? 'is-valid' : undefined} key={rule.label}>
                {rule.valid ? (
                  <Check size={15} aria-hidden="true" />
                ) : (
                  <Circle size={12} aria-hidden="true" />
                )}
                {rule.label}
              </li>
            ))}
          </ul>

          <PasswordField
            id="password-confirmation"
            label="Confirmar nueva contraseña"
            value={passwordConfirmation}
            autoComplete="new-password"
            placeholder="Repetí la nueva contraseña"
            visible={visibleField === 'confirmation'}
            onChange={(value) => {
              setPasswordConfirmation(value)
              setValidationError(null)
            }}
            onToggleVisibility={() => toggleVisibility('confirmation')}
          />

          {errorMessage && (
            <p className="form-error" role="alert" aria-live="polite">
              <CircleAlert size={18} aria-hidden="true" />
              {errorMessage}
            </p>
          )}

          <div className="password-change-actions">
            <button
              className="password-change-cancel"
              type="button"
              onClick={handleCancel}
              disabled={changePasswordMutation.isPending}
            >
              <ArrowLeft size={18} aria-hidden="true" />
              Volver
            </button>
            <button
              className="password-change-submit"
              type="submit"
              disabled={changePasswordMutation.isPending}
            >
              {changePasswordMutation.isPending ? (
                <LoaderCircle
                  className="loading-icon"
                  size={18}
                  aria-hidden="true"
                />
              ) : (
                <Save size={18} aria-hidden="true" />
              )}
              {changePasswordMutation.isPending ? 'Guardando…' : 'Guardar contraseña'}
            </button>
          </div>
        </form>
      </section>
    </main>
  )
}
