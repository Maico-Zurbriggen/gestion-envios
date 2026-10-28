import { useIsMutating, useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query'
import { useAppSelector } from '../../../app/store'
import { selectAuthToken } from '../../auth/redux/authSlice'
import { createRoute, generateRoutes, getDrivers, getPendingPackages, getRoute, getRoutes, getWaitingSummary, runRouteCommand, saveDriverProfile } from '../services/routesApi'
import type { DistanceType, DriverProfileInput, GenerateRoutesInput, NewRouteInput, RouteCommand, RouteRange } from '../types/route.types'

const mutationKey = ['route-operations']
const ROUTES_KEY = ['delivery-routes'] as const

export function useRoutesBusy() {
  return useIsMutating({ mutationKey }) > 0
}

/** Después de cualquier cambio: listados, paquetes en espera y seguimiento. */
function refresh(client: QueryClient) {
  return Promise.all([
    client.invalidateQueries({ queryKey: [...ROUTES_KEY, 'list'] }),
    client.invalidateQueries({ queryKey: [...ROUTES_KEY, 'pending'] }),
    client.invalidateQueries({ queryKey: ['tracking'] }),
  ])
}

export function useDrivers() {
  const token = useAppSelector(selectAuthToken)
  return useQuery({ queryKey: ['delivery-drivers'], queryFn: ({ signal }) => getDrivers(token!, signal), enabled: Boolean(token), retry: false })
}

export function useRoutes(range: RouteRange) {
  const token = useAppSelector(selectAuthToken)
  return useQuery({
    queryKey: [...ROUTES_KEY, 'list', range],
    queryFn: ({ signal }) => getRoutes(range, token!, signal),
    enabled: Boolean(token),
    retry: false,
    refetchInterval: 60_000,
  })
}

export function useRoute(id: string) {
  const token = useAppSelector(selectAuthToken)
  return useQuery({ queryKey: [...ROUTES_KEY, 'detail', id], queryFn: ({ signal }) => getRoute(id, token!, signal), enabled: Boolean(token && id), retry: false,
    // En reparto, las paradas cambian solas con cada entrega.
    refetchInterval: (query) => (query.state.data?.status === 'EN_CURSO' ? 30_000 : false) })
}

export function usePendingPackages(branchId: number, distanceType: DistanceType) {
  const token = useAppSelector(selectAuthToken)
  return useQuery({
    queryKey: [...ROUTES_KEY, 'pending', branchId, distanceType],
    queryFn: ({ signal }) => getPendingPackages(branchId, distanceType, token!, signal),
    enabled: Boolean(token && branchId),
    retry: false,
  })
}

export function useWaitingSummary() {
  const token = useAppSelector(selectAuthToken)
  return useQuery({
    queryKey: [...ROUTES_KEY, 'pending', 'summary'],
    queryFn: ({ signal }) => getWaitingSummary(token!, signal),
    enabled: Boolean(token),
    retry: false,
    refetchInterval: 60_000,
  })
}

export function useGenerateRoutes() {
  const token = useAppSelector(selectAuthToken)
  const client = useQueryClient()
  return useMutation({ mutationKey, mutationFn: (input: GenerateRoutesInput) => generateRoutes(input, token!), retry: false,
    onSuccess: async (result) => {
      for (const route of result.routes) client.setQueryData([...ROUTES_KEY, 'detail', route.id], route)
      await refresh(client)
    },
  })
}

export function useCreateRoute() {
  const token = useAppSelector(selectAuthToken)
  const client = useQueryClient()
  return useMutation({ mutationKey, mutationFn: (input: NewRouteInput) => createRoute(input, token!), retry: false,
    onSuccess: async (route) => {
      client.setQueryData([...ROUTES_KEY, 'detail', route.id], route)
      await refresh(client)
    },
  })
}

export function useRouteCommand() {
  const token = useAppSelector(selectAuthToken)
  const client = useQueryClient()
  return useMutation({ mutationKey, mutationFn: (command: RouteCommand) => runRouteCommand(command, token!), retry: false,
    onSuccess: async (result, command) => {
      if (result.route) client.setQueryData([...ROUTES_KEY, 'detail', command.id], result.route)
      else client.removeQueries({ queryKey: [...ROUTES_KEY, 'detail', command.id] })
      if (command.action === 'locate') await client.invalidateQueries({ queryKey: [...ROUTES_KEY, 'detail'] })
      await refresh(client)
    },
    onError: async () => {
      await Promise.all([
        client.invalidateQueries({ queryKey: ROUTES_KEY }),
        client.invalidateQueries({ queryKey: ['delivery-drivers'] }),
      ])
    },
  })
}

export function useSaveDriverProfile() {
  const token = useAppSelector(selectAuthToken)
  const client = useQueryClient()
  return useMutation({ mutationKey, mutationFn: (input: DriverProfileInput) => saveDriverProfile(input, token!), retry: false,
    onSuccess: () => client.invalidateQueries({ queryKey: ['delivery-drivers'] }) })
}
