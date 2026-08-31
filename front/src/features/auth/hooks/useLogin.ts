import { useMutation } from '@tanstack/react-query'
import { useAppDispatch } from '../../../app/store'
import { setCredentials } from '../redux/authSlice'
import { login } from '../services/authApi'

export function useLogin() {
  const dispatch = useAppDispatch()

  return useMutation({
    mutationFn: login,
    onSuccess: (session) => {
      dispatch(setCredentials(session))
    },
  })
}
