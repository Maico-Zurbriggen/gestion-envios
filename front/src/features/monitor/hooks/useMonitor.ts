import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAppSelector } from '../../../app/store'
import { selectAuthToken } from '../../auth/redux/authSlice'
import { listAdminClaims, updateClaimStatus, type ClaimStatus } from '../services/claimsAdminApi'
import { getMonitorSummary, getPackageTrace, listMonitorPackages, processDeadlines } from '../services/monitorApi'
import type { MonitorFilters } from '../types/monitor.types'

const MONITOR_KEY = ['admin', 'monitor'] as const
/** El monitor se refresca solo cada 30 segundos mientras está abierto. */
const AUTO_REFRESH_MS = 30_000

export function useMonitorSummary() {
  const token = useAppSelector(selectAuthToken)
  return useQuery({
    queryKey: [...MONITOR_KEY, 'summary'],
    queryFn: () => getMonitorSummary(token ?? ''),
    enabled: Boolean(token),
    refetchInterval: AUTO_REFRESH_MS,
  })
}

export function useMonitorPackages(filters: MonitorFilters) {
  const token = useAppSelector(selectAuthToken)
  return useQuery({
    queryKey: [...MONITOR_KEY, 'packages', filters],
    queryFn: ({ signal }) => listMonitorPackages(filters, token ?? '', signal),
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

export function useProcessDeadlines() {
  const token = useAppSelector(selectAuthToken)
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => {
      if (!token) throw new Error('La sesión venció. Volvé a iniciar sesión.')
      return processDeadlines(token)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: MONITOR_KEY }),
  })
}

export function useAdminClaims() {
  const token = useAppSelector(selectAuthToken)
  return useQuery({
    queryKey: [...MONITOR_KEY, 'claims'],
    queryFn: () => listAdminClaims(token ?? ''),
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
