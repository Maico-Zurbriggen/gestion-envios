import { useState, type FormEvent } from 'react'
import {
  CircleAlert,
  Eye,
  EyeOff,
  IdCard,
  LoaderCircle,
  LockKeyhole,
  LogIn,
  PackageCheck,
  ShieldCheck,
} from 'lucide-react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAppSelector } from '../../../app/store'
import { useLogin } from '../hooks/useLogin'
import { selectIsAuthenticated } from '../redux/authSlice'
import './LoginPage.css'

interface LoginLocationState {
  from?: {
    pathname?: string
    search?: string
    hash?: string
  }
}

function getReturnPath(state: unknown) {
  const { from } = (state ?? {}) as LoginLocationState

  if (!from?.pathname?.startsWith('/')) return '/'

  return `${from.pathname}${from.search ?? ''}${from.hash ?? ''}`
}

export function LoginPage() {
  const [dni, setDni] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const isAuthenticated = useAppSelector(selectIsAuthenticated)
  const loginMutation = useLogin()
  const location = useLocation()
  const navigate = useNavigate()

  if (isAuthenticated) {
    return <Navigate to="/" replace />
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    loginMutation.mutate(
      { dni: dni.trim(), password },
      {
        onSuccess: () => navigate(getReturnPath(location.state), { replace: true }),
      },
    )
  }

  const errorMessage =
    loginMutation.error instanceof Error ? loginMutation.error.message : null

  return (
    <main className="login-page">
      <section className="login-card" aria-labelledby="login-title">
        <aside className="login-brand">
          <div className="login-brand__identity">
            <span className="login-brand__mark" aria-hidden="true">
              <PackageCheck size={24} strokeWidth={2.25} />
            </span>
            <span>Gestión de envíos</span>
          </div>

          <div className="login-brand__content">
            <h2>Tu operación logística, en un solo lugar.</h2>
            <p>
              Administrá cada envío con información clara, segura y siempre
              disponible.
            </p>
          </div>

          <span className="login-brand__footer">
            <ShieldCheck size={17} aria-hidden="true" />
            Control y trazabilidad para todo el equipo
          </span>
        </aside>

        <div className="login-panel">
          <header className="login-panel__header">
            <span className="eyebrow">Bienvenido</span>
            <h1 id="login-title">Iniciar sesión</h1>
            <p>Ingresá tus credenciales para acceder al panel.</p>
          </header>

          <form className="login-form" onSubmit={handleSubmit}>
            <div className="form-field">
              <label htmlFor="dni">DNI</label>
              <div className="input-control">
                <IdCard
                  className="input-control__icon"
                  size={19}
                  aria-hidden="true"
                />
                <input
                  className="form-control form-control--with-icon"
                  id="dni"
                  name="dni"
                  type="text"
                  inputMode="numeric"
                  autoComplete="username"
                  placeholder="Ingresá tu DNI"
                  value={dni}
                  onChange={(event) =>
                    setDni(event.target.value.replace(/\D/g, ''))
                  }
                  disabled={loginMutation.isPending}
                  pattern="[0-9]{6,20}"
                  minLength={6}
                  maxLength={20}
                  required
                  autoFocus
                />
              </div>
            </div>

            <div className="form-field">
              <label htmlFor="password">Contraseña</label>
              <div className="input-control">
                <LockKeyhole
                  className="input-control__icon"
                  size={19}
                  aria-hidden="true"
                />
                <input
                  className="form-control form-control--with-icon form-control--with-action"
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  placeholder="Ingresá tu contraseña"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  disabled={loginMutation.isPending}
                  required
                />
                <button
                  className="password-toggle"
                  type="button"
                  onClick={() => setShowPassword((currentValue) => !currentValue)}
                  aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                  aria-pressed={showPassword}
                >
                  {showPassword ? (
                    <EyeOff size={19} aria-hidden="true" />
                  ) : (
                    <Eye size={19} aria-hidden="true" />
                  )}
                </button>
              </div>
            </div>

            {errorMessage && (
              <p className="login-error" role="alert" aria-live="polite">
                <CircleAlert size={18} aria-hidden="true" />
                {errorMessage}
              </p>
            )}

            <button
              className="login-submit"
              type="submit"
              disabled={loginMutation.isPending}
            >
              {loginMutation.isPending ? (
                <LoaderCircle
                  className="login-submit__spinner"
                  size={18}
                  aria-hidden="true"
                />
              ) : (
                <LogIn size={18} aria-hidden="true" />
              )}
              {loginMutation.isPending ? 'Ingresando…' : 'Ingresar'}
            </button>
          </form>
        </div>
      </section>
    </main>
  )
}
