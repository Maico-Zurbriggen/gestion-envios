import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAppDispatch, useAppSelector } from '../../../app/store'
import { selectAuthToken, setCredentials } from '../../auth/redux/authSlice'
import { loginWithToken } from '../../auth/services/authApi'
import { listAdminBranches, saveBranch } from '../services/branchesAdminApi'
import type { BranchInput } from '../types/branch.types'

const ADMIN_BRANCHES_KEY = ['admin', 'branches'] as const

export function useAdminBranches(enabled = true) {
  const token = useAppSelector(selectAuthToken)
  return useQuery({
    queryKey: ADMIN_BRANCHES_KEY,
    queryFn: () => listAdminBranches(token ?? ''),
    enabled: Boolean(token) && enabled,
  })
}

export function useSaveBranch() {
  const token = useAppSelector(selectAuthToken)
  const dispatch = useAppDispatch()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, input }: { id: number | null; input: BranchInput }) => {
      if (!token) throw new Error('La sesión venció. Volvé a iniciar sesión.')
      return saveBranch(id, input, token)
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ADMIN_BRANCHES_KEY }),
        // El catálogo público (registro de envíos, retiro) también cambió.
        queryClient.invalidateQueries({ queryKey: ['branches'] }),
      ])
      // Las sucursales del selector de arriba salen de la sesión: se actualizan sin volver a ingresar.
      const session = await loginWithToken({ token: token! }).catch(() => null)
      if (session?.type === 'authenticated') dispatch(setCredentials(session.session))
    },
  })
}
