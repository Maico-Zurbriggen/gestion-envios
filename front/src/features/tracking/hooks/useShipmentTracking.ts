import { useQuery } from '@tanstack/react-query'
import { getShipmentTracking, TrackingApiError } from '../services/trackingApi'

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
  })
}
