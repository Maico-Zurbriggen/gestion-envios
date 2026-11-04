import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ClaimsApiError, createClaim, getClaimContext } from '../services/claimsApi'
import type { ClaimContext, ClaimFormValues } from '../types/claim.types'

const claimKey = (token: string) => ['shipment-claims', token] as const

export function useShipmentClaims(token: string, enabled: boolean) {
  return useQuery({
    queryKey: claimKey(token),
    queryFn: ({ signal }) => getClaimContext(token, signal),
    enabled,
    retry: false,
    staleTime: 0,
  })
}

export function useCreateClaim(token: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: ClaimFormValues) => createClaim(token, input),
    retry: false,
    onSuccess: (claim) => {
      queryClient.setQueryData<ClaimContext>(claimKey(token), (context) => {
        if (!context) return context
        const claims = [claim, ...context.claims.filter((item) => item.id !== claim.id)]
        const activeCount = claims.filter((item) => item.status === 'ABIERTO' || item.status === 'EN_REVISION').length
        return {
          ...context, claims, canCreate: activeCount < context.maxActiveClaims,
          unavailableReason: activeCount >= context.maxActiveClaims
            ? 'Alcanzaste el límite de reclamos en curso. Esperá una respuesta antes de iniciar otro.'
            : context.unavailableReason,
        }
      })
      void queryClient.invalidateQueries({ queryKey: claimKey(token) })
    },
    onError: (error) => {
      if (error instanceof ClaimsApiError && (error.status === 400 || error.status === 409)) {
        void queryClient.invalidateQueries({ queryKey: claimKey(token) })
      }
    },
  })
}
