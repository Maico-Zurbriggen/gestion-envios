import { useQuery } from '@tanstack/react-query'
import { getPickupOptions, getShipmentTracking, TrackingApiError } from '../services/trackingApi'

export function useShipmentTracking(token: string) {
  return useQuery({
    queryKey: ['tracking', token],
    queryFn: () => getShipmentTracking(token),
    enabled: Boolean(token),
    retry: (failureCount, error) => {
      if (error instanceof TrackingApiError && error.status === 404) return false
      return failureCount < 1
    },
    staleTime: 30 * 1000,
    refetchInterval: (query) => query.state.data?.packages.some((item) => ['EN_REPARTO', 'EN_TRANSITO'].includes(item.status)) ? 15000 : false,
  })
}

export function usePickupOptions(token: string, enabled: boolean, statusKey: string) {
  return useQuery({
    // El estado de los paquetes forma parte de la clave: cuando el seguimiento
    // cambia (llegó a la sucursal) se vuelve a consultar la disponibilidad.
    queryKey: ['tracking', token, 'pickup-options', statusKey],
    queryFn: ({ signal }) => getPickupOptions(token, signal),
    enabled: Boolean(token) && enabled,
    retry: (failureCount, error) => !(error instanceof TrackingApiError && error.status === 404) && failureCount < 1,
    staleTime: 30 * 1000,
  })
}
