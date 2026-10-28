import { useQuery } from '@tanstack/react-query'
import { useAppSelector } from '../../../app/store'
import { selectAuthToken } from '../../auth/redux/authSlice'
import { getRoadRoute, planRoadRoute } from '../services/roadRouteApi'
import type { DeliveryRoute } from '../types/route.types'
import type { RoadRoutingState } from '../types/roadRoute.types'

export function useRoadRoute(route: DeliveryRoute | undefined): RoadRoutingState {
  const token = useAppSelector(selectAuthToken)
  const plan = route ? planRoadRoute(route) : null
  const query = useQuery({
    queryKey: ['road-route', plan?.points ?? []],
    queryFn: ({ signal }) => getRoadRoute(plan!.points, token!, signal),
    enabled: Boolean(token && plan && plan.points.length > 1),
    staleTime: 30 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
    retry: false,
    refetchOnWindowFocus: false,
  })
  return {
    data: query.data,
    loading: query.isFetching && !query.data,
    missingStops: plan?.missingStops ?? 0,
    points: plan?.points ?? [],
  }
}
