import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAppSelector } from '../../../app/store'
import { selectActiveBranchId, selectAuthToken } from '../../auth/redux/authSlice'
import { listAdminClaims, updateClaimStatus, type ClaimStatus } from '../services/claimsAdminApi'
import { getMonitorSummary, getPackageTrace, listMonitorPackages } from '../services/monitorApi'
import type { MonitorFilters } from '../types/monitor.types'

const MONITOR_KEY = ['admin', 'monitor'] as const
/** El monitor se refresca solo cada 30 segundos mientras está abierto. */
const AUTO_REFRESH_MS = 30_000

// Todo el monitor muestra la sucursal en la que se está trabajando.
export function useMonitorSummary() {
  const token = useAppSelector(selectAuthToken)
  const branchId = useAppSelector(selectActiveBranchId)
  return useQuery({
    queryKey: [...MONITOR_KEY, 'summary', branchId],
    queryFn: () => getMonitorSummary(token ?? '', branchId),
    enabled: Boolean(token),
    refetchInterval: AUTO_REFRESH_MS,
  })
}

export function useMonitorPackages(filters: MonitorFilters) {
  const token = useAppSelector(selectAuthToken)
  const branchId = useAppSelector(selectActiveBranchId)
  const scoped = { ...filters, branchId }
  return useQuery({
    queryKey: [...MONITOR_KEY, 'packages', scoped],
    queryFn: ({ signal }) => listMonitorPackages(scoped, token ?? '', signal),
    enabled: Boolean(token),
    placeholderData: keepPreviousData,
    refetchInterval: AUTO_REFRESH_MS,
  })
}

export function usePackageTrace(code: string | undefined) {
  const token = useAppSelector(selectAuthToken)
  return useQuery({
    queryKey: [...MONITOR_KEY, 'trace', code?.toUpperCase()],
    queryFn: () => getPackageTrace(code ?? '', token ?? ''),
    enabled: Boolean(token && code),
    retry: false,
    refetchInterval: AUTO_REFRESH_MS,
  })
}

export function useAdminClaims() {
  const token = useAppSelector(selectAuthToken)
  const branchId = useAppSelector(selectActiveBranchId)
  return useQuery({
    queryKey: [...MONITOR_KEY, 'claims', branchId],
    queryFn: () => listAdminClaims(token ?? '', branchId),
    enabled: Boolean(token),
    refetchInterval: AUTO_REFRESH_MS,
  })
}

export function useUpdateClaim() {
  const token = useAppSelector(selectAuthToken)
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status, resolution }: { id: string; status: ClaimStatus; resolution: string }) => {
      if (!token) throw new Error('La sesión venció. Volvé a iniciar sesión.')
      return updateClaimStatus(id, status, resolution, token)
    },
    // Un reclamo cerrado cambia los contadores del monitor y la traza del paquete.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: MONITOR_KEY }),
  })
}
