import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAppSelector } from '../../../app/store'
import { selectAuthToken } from '../../auth/redux/authSlice'
import { getShipmentNotifications, retryShipmentNotifications } from '../services/notificationsApi'

export function useShipmentNotifications(trackingToken: string) {
  const token = useAppSelector(selectAuthToken)
  const client = useQueryClient()
  const queryKey = ['shipment-notifications', trackingToken]
  const notifications = useQuery({
    queryKey,
    queryFn: ({ signal }) => getShipmentNotifications(trackingToken, token!, signal),
    enabled: Boolean(trackingToken && token),
    retry: false,
    staleTime: 0,
    // El despacho inicial corre en segundo plano: mientras haya pendientes se vuelve a consultar.
    refetchInterval: (query) => query.state.data?.some((item) => item.status === 'PENDIENTE') ? 5000 : false,
  })
  const retry = useMutation({
    mutationFn: () => retryShipmentNotifications(trackingToken, token!),
    onSuccess: (data) => client.setQueryData(queryKey, data),
  })
  return { notifications, retry }
}
