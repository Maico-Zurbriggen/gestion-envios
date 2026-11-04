import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAppSelector } from '../../../app/store'
import { selectAuthToken } from '../../auth/redux/authSlice'
import { receivePackage, scanPackage } from '../services/terminalApi'
import type { ReceptionInput } from '../types/terminal.types'

export function useTerminal(code: string) {
  const token = useAppSelector(selectAuthToken)
  const client = useQueryClient()
  const scan = useQuery({ queryKey: ['terminal-package', code], queryFn: ({ signal }) => scanPackage(code, token!, signal), enabled: Boolean(code && token), retry: false, staleTime: 0 })
  const receive = useMutation({
    mutationFn: (input: ReceptionInput) => receivePackage(input, token!),
    onSettled: () => { void client.invalidateQueries({ queryKey: ['terminal-package'] }); void client.invalidateQueries({ queryKey: ['tracking'] }); void client.invalidateQueries({ queryKey: ['delivery-routes'] }) },
  })
  return { scan, receive }
}
