import { useMutation } from '@tanstack/react-query'
import { createShipment } from '../services/shipmentsApi'

export function useCreateShipment() {
  return useMutation({ mutationFn: createShipment })
}
