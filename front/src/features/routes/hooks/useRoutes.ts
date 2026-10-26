import { useIsMutating, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAppSelector } from '../../../app/store'
import { selectAuthToken } from '../../auth/redux/authSlice'
import { generateRoutes, getDrivers, getRoute, getRouteAlerts, getRoutes, resolveRouteAlert, runRouteCommand, saveDriverProfile } from '../services/routesApi'
import type { DriverProfileInput, GenerateRoutesInput, RouteCommand, RouteFilters } from '../types/route.types'

const mutationKey = ['route-operations']

export function useRoutesBusy() {
  return useIsMutating({ mutationKey }) > 0
}

export function useDrivers() {
  const token = useAppSelector(selectAuthToken)
  return useQuery({ queryKey: ['delivery-drivers'], queryFn: ({ signal }) => getDrivers(token!, signal), enabled: Boolean(token), retry: false })
}

export function useRoutes(filters: RouteFilters) {
  const token = useAppSelector(selectAuthToken)
  return useQuery({ queryKey: ['delivery-routes', 'list', filters], queryFn: ({ signal }) => getRoutes(filters, token!, signal), enabled: Boolean(token && filters.date), retry: false })
}

export function useRoute(id: string) {
  const token = useAppSelector(selectAuthToken)
  return useQuery({ queryKey: ['delivery-routes', 'detail', id], queryFn: ({ signal }) => getRoute(id, token!, signal), enabled: Boolean(token && id), retry: false })
}

export function useRouteAlerts(branchId: number) {
  const token = useAppSelector(selectAuthToken)
  return useQuery({ queryKey: ['delivery-routes', 'alerts', branchId], queryFn: ({ signal }) => getRouteAlerts(branchId, token!, signal), enabled: Boolean(token), retry: false })
}

export function useGenerateRoutes() {
  const token = useAppSelector(selectAuthToken)
  const client = useQueryClient()
  return useMutation({ mutationKey, mutationFn: (input: GenerateRoutesInput) => generateRoutes(input, token!), retry: false,
    onSuccess: async (result) => {
      for (const route of result.routes) client.setQueryData(['delivery-routes', 'detail', route.id], route)
      await client.invalidateQueries({ queryKey: ['delivery-routes', 'list'] })
      await client.invalidateQueries({ queryKey: ['delivery-routes', 'alerts'] })
    },
  })
}

export function useRouteCommand() {
  const token = useAppSelector(selectAuthToken)
  const client = useQueryClient()
  return useMutation({ mutationKey, mutationFn: (command: RouteCommand) => runRouteCommand(command, token!), retry: false,
    onSuccess: async (result, command) => {
      if (result.route) client.setQueryData(['delivery-routes', 'detail', command.id], result.route)
      else client.removeQueries({ queryKey: ['delivery-routes', 'detail', command.id] })
      await Promise.all([
        client.invalidateQueries({ queryKey: ['delivery-routes', 'list'] }),
        ...(command.action === 'locate' ? [client.invalidateQueries({ queryKey: ['delivery-routes', 'detail'] })] : []),
        client.invalidateQueries({ queryKey: ['delivery-routes', 'alerts'] }),
        client.invalidateQueries({ queryKey: ['tracking'] }),
      ])
    },
    onError: async () => {
      await Promise.all([
        client.invalidateQueries({ queryKey: ['delivery-routes'] }),
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

export function useResolveRouteAlert() {
  const token = useAppSelector(selectAuthToken)
  const client = useQueryClient()
  return useMutation({ mutationKey, mutationFn: (id: string) => resolveRouteAlert(id, token!), retry: false,
    onSuccess: () => client.invalidateQueries({ queryKey: ['delivery-routes', 'alerts'] }) })
}
