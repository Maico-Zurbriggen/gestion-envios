import { useMutation } from '@tanstack/react-query'
import { geocodeDestination } from '../services/geocodingApi'

export function useGeocodeDestination() {
  return useMutation({ mutationFn: geocodeDestination })
}
