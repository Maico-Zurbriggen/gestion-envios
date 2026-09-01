import { useEffect, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { LoaderCircle, LogOut, PackageCheck, RefreshCw } from 'lucide-react'
import { useAppDispatch, useAppSelector } from '../../../app/store'
import {
  clearCredentials,
  selectAuthStatus,
  selectAuthToken,
  selectCurrentUser,
  setCredentials,
  setPasswordChangeRequired,
} from '../redux/authSlice'
import { AuthApiError, loginWithToken } from '../services/authApi'
import './AuthBootstrap.css'

interface AuthBootstrapProps {
  children: ReactNode
}

export function AuthBootstrap({ children }: AuthBootstrapProps) {
  const dispatch = useAppDispatch()
  const status = useAppSelector(selectAuthStatus)
  const token = useAppSelector(selectAuthToken)
  const user = useAppSelector(selectCurrentUser)
  const isPublicShipmentRoute = window.location.pathname === '/envios/nuevo'

  const sessionQuery = useQuery({
    queryKey: ['auth', 'session-validation'],
    queryFn: () => loginWithToken({ token: token! }, user?.dni ?? ''),
    enabled: status === 'checking' && Boolean(token),
    retry: false,
  })

  useEffect(() => {
    if (status !== 'checking') return

    if (!token) {
      dispatch(clearCredentials())
      return
    }

    if (sessionQuery.data?.type === 'authenticated') {
      dispatch(setCredentials(sessionQuery.data.session))
    }

    if (sessionQuery.data?.type === 'passwordChangeRequired') {
      dispatch(setPasswordChangeRequired(sessionQuery.data.challenge))
    }
  }, [dispatch, sessionQuery.data, status, token])

  useEffect(() => {
    if (status !== 'checking' || !sessionQuery.error) return

    const error = sessionQuery.error
    const isRejectedSession =
      error instanceof AuthApiError &&
      error.status !== undefined &&
      error.status >= 400 &&
      error.status < 500

    if (isRejectedSession) dispatch(clearCredentials())
  }, [dispatch, sessionQuery.error, status])

  if (status !== 'checking' || isPublicShipmentRoute) return children

  if (sessionQuery.isError) {
    const isRejectedSession =
      sessionQuery.error instanceof AuthApiError &&
      sessionQuery.error.status !== undefined &&
      sessionQuery.error.status >= 400 &&
      sessionQuery.error.status < 500

    if (!isRejectedSession) {
      return (
        <main className="auth-bootstrap">
          <section className="auth-bootstrap__card" aria-live="polite">
            <span className="auth-bootstrap__icon" aria-hidden="true">
              <PackageCheck size={30} />
            </span>
            <h1>No pudimos validar tu sesión</h1>
            <p>
              Tus datos siguen guardados. Comprobá la conexión o que el servidor
              esté disponible y volvé a intentarlo.
            </p>
            <div className="auth-bootstrap__actions">
              <button
                className="auth-bootstrap__button auth-bootstrap__button--primary"
                type="button"
                disabled={sessionQuery.isFetching}
                onClick={() => void sessionQuery.refetch()}
              >
                {sessionQuery.isFetching ? (
                  <LoaderCircle className="auth-bootstrap__spinner" size={18} />
                ) : (
                  <RefreshCw size={18} />
                )}
                Reintentar
              </button>
              <button
                className="auth-bootstrap__button"
                type="button"
                onClick={() => dispatch(clearCredentials())}
              >
                <LogOut size={18} />
                Volver al login
              </button>
            </div>
          </section>
        </main>
      )
    }
  }

  return (
    <main className="auth-bootstrap" aria-live="polite" aria-busy="true">
      <section className="auth-bootstrap__card auth-bootstrap__card--loading">
        <LoaderCircle
          className="auth-bootstrap__spinner auth-bootstrap__spinner--large"
          size={34}
          aria-hidden="true"
        />
        <h1>Validando tu sesión</h1>
        <p>Estamos comprobando que tu acceso siga activo.</p>
      </section>
    </main>
  )
}
