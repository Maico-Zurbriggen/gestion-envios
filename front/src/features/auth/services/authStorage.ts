import type {
  AuthSession,
  PasswordChangeChallenge,
} from '../types/auth.types'

const AUTH_STORAGE_KEY = 'gestion-envios.auth-session'
const PASSWORD_CHANGE_STORAGE_KEY = 'gestion-envios.password-change'

function isStoredSession(value: unknown): value is AuthSession {
  if (!value || typeof value !== 'object') return false

  const session = value as Partial<AuthSession>
  const user = session.user as Partial<AuthSession['user']> | undefined

  return (
    typeof session.token === 'string' &&
    session.token.length > 0 &&
    typeof user?.id === 'string' &&
    (typeof user.name === 'string' || user.name === null) &&
    (typeof user.email === 'string' || user.email === null) &&
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

export function loadPasswordChangeChallenge(): PasswordChangeChallenge | null {
  try {
    const storedChallenge = sessionStorage.getItem(PASSWORD_CHANGE_STORAGE_KEY)
    if (!storedChallenge) return null

    const challenge = JSON.parse(storedChallenge) as Partial<PasswordChangeChallenge>
    if (typeof challenge.token !== 'string' || typeof challenge.dni !== 'string') {
      return null
    }

    return { token: challenge.token, dni: challenge.dni }
  } catch {
    return null
  }
}

export function savePasswordChangeChallenge(
  challenge: PasswordChangeChallenge,
) {
  sessionStorage.setItem(PASSWORD_CHANGE_STORAGE_KEY, JSON.stringify(challenge))
}

export function removePasswordChangeChallenge() {
  sessionStorage.removeItem(PASSWORD_CHANGE_STORAGE_KEY)
}
