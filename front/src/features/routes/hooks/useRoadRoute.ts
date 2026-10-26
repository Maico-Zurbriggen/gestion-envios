import { useQuery } from '@tanstack/react-query'
import { getMapboxRoadRoute, planRoadRoute } from '../services/mapboxRoutingApi'
import type { DeliveryRoute } from '../types/route.types'
import type { RoadRoutingState } from '../types/roadRoute.types'

export function useRoadRoute(route: DeliveryRoute | undefined): RoadRoutingState {
  const plan = route ? planRoadRoute(route) : null
  const query = useQuery({
    queryKey: ['mapbox-road-route', 'driving', plan?.points ?? []],
    queryFn: ({ signal }) => getMapboxRoadRoute(plan!.points, signal),
    enabled: Boolean(plan && !plan.error),
    staleTime: 30 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
    retry: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  })
  return {
    data: !plan?.error && !query.isError ? query.data : undefined,
    error: plan?.error ?? query.error,
    loading: Boolean(plan && !plan.error && query.isPending),
    fetching: query.isFetching,
    missingStops: plan?.missingStops ?? 0,
    canRetry: Boolean(plan && !plan.error),
    retry: () => { void query.refetch() },
  }
}
