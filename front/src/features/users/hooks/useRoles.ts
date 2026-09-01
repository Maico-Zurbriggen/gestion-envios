import { useQuery } from '@tanstack/react-query'
import { getRoles } from '../services/usersApi'

export function useRoles() {
  return useQuery({
    queryKey: ['roles'],
    queryFn: getRoles,
    staleTime: 5 * 60 * 1000,
  })
}
