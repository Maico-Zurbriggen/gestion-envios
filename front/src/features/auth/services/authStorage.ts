import type { AuthSession } from '../types/auth.types'

const AUTH_STORAGE_KEY = 'gestion-envios.auth-session'

function isStoredSession(value: unknown): value is AuthSession {
  if (!value || typeof value !== 'object') return false

  const session = value as Partial<AuthSession>
  const user = session.user as Partial<AuthSession['user']> | undefined

  return (
    typeof session.token === 'string' &&
    session.token.length > 0 &&
    typeof user?.id === 'string' &&
    typeof user.name === 'string' &&
    typeof user.email === 'string' &&
    typeof user.role === 'string'
  )
}

export function loadAuthSession(): AuthSession | null {
  try {
    const storedSession = localStorage.getItem(AUTH_STORAGE_KEY)
    if (!storedSession) return null

    const parsedSession: unknown = JSON.parse(storedSession)
    return isStoredSession(parsedSession) ? parsedSession : null
  } catch {
    return null
  }
}

export function saveAuthSession(session: AuthSession) {
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session))
}

export function removeAuthSession() {
  localStorage.removeItem(AUTH_STORAGE_KEY)
}
