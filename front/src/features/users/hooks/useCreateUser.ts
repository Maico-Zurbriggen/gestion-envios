import { useMutation } from '@tanstack/react-query'
import { useAppSelector } from '../../../app/store'
import { selectAuthToken } from '../../auth/redux/authSlice'
import { createUser } from '../services/usersApi'

export function useCreateUser() {
  const token = useAppSelector(selectAuthToken)

  return useMutation({
    mutationFn: async (input: Parameters<typeof createUser>[0]) => {
      if (!token) throw new Error('La sesión venció. Volvé a iniciar sesión.')
      return createUser(input, token)
    },
  })
}
