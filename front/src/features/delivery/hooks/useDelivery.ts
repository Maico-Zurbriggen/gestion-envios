import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAppSelector } from '../../../app/store'
import { selectAuthToken } from '../../auth/redux/authSlice'
import { getContact, getMyRoute, getMyRoutes, getPosition, registerDelivery, startMyRoute } from '../services/deliveryApi'
import type { DeliveryOperation } from '../types/delivery.types'

export function useMyRoutes(date: string, status: string) {
  const token = useAppSelector(selectAuthToken)
  return useQuery({ queryKey: ['delivery', 'list', date, status], queryFn: ({ signal }) => getMyRoutes(date, status, token!, signal), enabled: Boolean(token), retry: false, refetchInterval: 30000 })
}
export function useMyRoute(id: string) {
  const token = useAppSelector(selectAuthToken)
  const client = useQueryClient()
  const detail = useQuery({ queryKey: ['delivery', 'detail', id], queryFn: ({ signal }) => getMyRoute(id, token!, signal), enabled: Boolean(id && token), retry: false, refetchInterval: (query) => query.state.data?.status === 'EN_CURSO' ? 15000 : false })
  const position = useQuery({ queryKey: ['delivery', 'position', id], queryFn: ({ signal }) => getPosition(id, token!, signal), enabled: Boolean(id && token), retry: false, refetchInterval: detail.data?.status === 'EN_CURSO' ? 15000 : false })
  const start = useMutation({ mutationFn: () => startMyRoute(id, token!), onSuccess: (route) => { client.setQueryData(['delivery', 'detail', id], route); void client.invalidateQueries({ queryKey: ['delivery', 'list'] }); void client.invalidateQueries({ queryKey: ['tracking'] }) } })
  return { detail, position, start }
}
export function useRecipientContact(id: string, code: string) {
  const token = useAppSelector(selectAuthToken)
  return useQuery({ queryKey: ['delivery', 'contact', id, code], queryFn: ({ signal }) => getContact(id, code, token!, signal), retry: false, gcTime: 0 })
}
export function useDeliveryOperation(id: string, code: string) {
  const token = useAppSelector(selectAuthToken)
  const client = useQueryClient()
  return useMutation({ mutationFn: (input: DeliveryOperation) => registerDelivery(id, code, input, token!), retry: false,
    onSuccess: () => { void client.invalidateQueries({ queryKey: ['delivery'] }); void client.invalidateQueries({ queryKey: ['tracking'] }); void client.invalidateQueries({ queryKey: ['delivery-routes'] }) },
  })
}
