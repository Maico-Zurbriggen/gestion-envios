import { useMutation } from '@tanstack/react-query'
import { useAppDispatch } from '../../../app/store'
import {
  setCredentials,
  setPasswordChangeRequired,
} from '../redux/authSlice'
import { login } from '../services/authApi'

export function useLogin() {
  const dispatch = useAppDispatch()

  return useMutation({
    mutationFn: login,
    onSuccess: (result) => {
      if (result.type === 'passwordChangeRequired') {
        dispatch(setPasswordChangeRequired(result.challenge))
        return
      }

      dispatch(setCredentials(result.session))
    },
  })
}
