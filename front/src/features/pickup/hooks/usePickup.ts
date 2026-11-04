import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAppSelector } from '../../../app/store'
import { selectAuthToken } from '../../auth/redux/authSlice'
import { registerPickup, validatePickup } from '../services/pickupApi'
import type { RegisterPickupInput } from '../types/pickup.types'

export function usePickupValidation(code: string) {
  const token = useAppSelector(selectAuthToken)
  return useQuery({
    queryKey: ['pickup-validation', code],
    queryFn: ({ signal }) => validatePickup(code, token!, signal),
    enabled: Boolean(code && token),
    retry: false,
    staleTime: 0,
  })
}

export function useRegisterPickup() {
  const token = useAppSelector(selectAuthToken)
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: RegisterPickupInput) => registerPickup(input, token!),
    // También ante un conflicto (otro mostrador ya lo entregó) hay que releer el estado.
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ['pickup-validation'] })
      void queryClient.invalidateQueries({ queryKey: ['tracking'] })
    },
  })
}
