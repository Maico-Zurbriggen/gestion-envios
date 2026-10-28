import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAppSelector } from '../../../app/store'
import { selectAuthToken } from '../../auth/redux/authSlice'
import {
  closeUnloadControl,
  getRoutesToControl,
  getUnloadControl,
  registerRead,
  startUnloadControl,
  type ControlType,
} from '../services/unloadApi'

const UNLOAD_KEY = ['terminal', 'unload'] as const

function useToken() {
  const token = useAppSelector(selectAuthToken)
  return () => {
    if (!token) throw new Error('La sesión venció. Volvé a iniciar sesión.')
    return token
  }
}

export function useRoutesToControl(branchId: number | null, type: ControlType) {
  const token = useAppSelector(selectAuthToken)
  return useQuery({
    queryKey: [...UNLOAD_KEY, 'incoming', type, branchId],
    queryFn: () => getRoutesToControl(branchId ?? 0, type, token ?? ''),
    enabled: Boolean(token && branchId),
    refetchInterval: 30_000,
  })
}

export function useUnloadControl(id: string | null) {
  const token = useAppSelector(selectAuthToken)
  return useQuery({
    queryKey: [...UNLOAD_KEY, 'control', id],
    queryFn: () => getUnloadControl(id ?? '', token ?? ''),
    enabled: Boolean(token && id),
    retry: false,
  })
}

export function useUnloadMutations() {
  const requireToken = useToken()
  const queryClient = useQueryClient()
  // Cada lectura devuelve el control actualizado: se guarda sin pedirlo de nuevo.
  const store = (control: { id: string }) => queryClient.setQueryData([...UNLOAD_KEY, 'control', control.id], control)

  return {
    start: useMutation({
      mutationFn: ({ routeId, branchId, type }: { routeId: string; branchId: number; type: ControlType }) =>
        startUnloadControl(routeId, branchId, type, requireToken()),
      onSuccess: (control) => {
        store(control)
        void queryClient.invalidateQueries({ queryKey: [...UNLOAD_KEY, 'incoming'] })
      },
    }),
    read: useMutation({
      mutationFn: ({ controlId, code }: { controlId: string; code: string }) => registerRead(controlId, code, requireToken()),
      onSuccess: (outcome) => store(outcome.control),
    }),
    close: useMutation({
      mutationFn: ({ controlId, notes }: { controlId: string; notes: string }) => closeUnloadControl(controlId, notes, requireToken()),
      onSuccess: ({ control }) => {
        store(control)
        void queryClient.invalidateQueries({ queryKey: [...UNLOAD_KEY, 'incoming'] })
        void queryClient.invalidateQueries({ queryKey: ['admin', 'monitor'] })
      },
    }),
  }
}
