import { useQuery } from '@tanstack/react-query'
import { getBranches } from '../services/shipmentsApi'

export function useBranches() {
  return useQuery({
    queryKey: ['branches'],
    queryFn: getBranches,
    staleTime: 10 * 60 * 1000,
  })
}
