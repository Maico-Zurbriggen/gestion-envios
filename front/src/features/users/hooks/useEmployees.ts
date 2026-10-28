import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAppSelector } from '../../../app/store'
import { selectAuthToken } from '../../auth/redux/authSlice'
import {
  changeEmployeeStatus,
  createUser,
  listEmployees,
  resetEmployeePassword,
  updateEmployee,
} from '../services/usersApi'
import type { CreateUserInput, EmployeeFilters, EmployeeStatus, UpdateEmployeeInput } from '../types/user.types'

const EMPLOYEES_KEY = ['admin', 'employees'] as const

function useToken() {
  const token = useAppSelector(selectAuthToken)
  return () => {
    if (!token) throw new Error('La sesión venció. Volvé a iniciar sesión.')
    return token
  }
}

export function useEmployees(filters: EmployeeFilters) {
  const token = useAppSelector(selectAuthToken)
  return useQuery({
    queryKey: [...EMPLOYEES_KEY, filters],
    queryFn: () => listEmployees(filters, token ?? ''),
    enabled: Boolean(token),
    placeholderData: keepPreviousData,
  })
}

/** Alta, edición, baja/reactivación y blanqueo; cada una refresca el listado. */
export function useEmployeeMutations() {
  const requireToken = useToken()
  const queryClient = useQueryClient()
  const invalidate = () => queryClient.invalidateQueries({ queryKey: EMPLOYEES_KEY })

  return {
    create: useMutation({
      mutationFn: (input: CreateUserInput) => createUser(input, requireToken()),
      onSuccess: invalidate,
    }),
    update: useMutation({
      mutationFn: ({ id, input }: { id: string; input: UpdateEmployeeInput }) => updateEmployee(id, input, requireToken()),
      onSuccess: invalidate,
    }),
    changeStatus: useMutation({
      mutationFn: ({ id, status }: { id: string; status: EmployeeStatus }) => changeEmployeeStatus(id, status, requireToken()),
      onSuccess: invalidate,
    }),
    resetPassword: useMutation({
      mutationFn: (id: string) => resetEmployeePassword(id, requireToken()),
      onSuccess: invalidate,
    }),
  }
}
