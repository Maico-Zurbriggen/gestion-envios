import { useMutation } from '@tanstack/react-query'
import { useAppDispatch, useAppSelector } from '../../../app/store'
import {
  selectAuthToken,
  selectCurrentUser,
  selectPasswordChangeChallenge,
  setCredentials,
} from '../redux/authSlice'
import { changePassword } from '../services/authApi'
import type {
  AuthUser,
  ChangePasswordCredentials,
} from '../types/auth.types'

function readTokenClaims(token: string) {
  try {
    const encodedPayload = token.split('.')[1]
    const normalizedPayload = encodedPayload.replace(/-/g, '+').replace(/_/g, '/')
    const paddedPayload = normalizedPayload.padEnd(
      Math.ceil(normalizedPayload.length / 4) * 4,
      '=',
    )

    return JSON.parse(atob(paddedPayload)) as Record<string, unknown>
  } catch {
    return {}
  }
}

function createFallbackUser(token: string, dni: string): AuthUser {
  const claims = readTokenClaims(token)

  return {
    id: typeof claims.sub === 'string' ? claims.sub : dni,
    name: null,
    dni,
    email: null,
    role: typeof claims.rol === 'string' ? claims.rol : '',
    requiresPasswordChange: false,
  }
}

export function useChangePassword() {
  const dispatch = useAppDispatch()
  const authToken = useAppSelector(selectAuthToken)
  const currentUser = useAppSelector(selectCurrentUser)
  const challenge = useAppSelector(selectPasswordChangeChallenge)

  return useMutation({
    mutationFn: async (credentials: ChangePasswordCredentials) => {
      const token = challenge?.token ?? authToken
      const dni = challenge?.dni ?? currentUser?.dni

      if (!token || !dni) {
        throw new Error('La sesión para cambiar la contraseña venció.')
      }

      const result = await changePassword(credentials, token)
      const user = currentUser
        ? { ...currentUser, requiresPasswordChange: false }
        : createFallbackUser(result.authToken, dni)

      return {
        message: result.message,
        session: { token: result.authToken, user },
      }
    },
    onSuccess: ({ session }) => {
      dispatch(setCredentials(session))
    },
  })
}
