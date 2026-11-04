import { useAppDispatch, useAppSelector } from '../../../app/store'
import { selectActiveBranch, selectCurrentUser, setActiveBranch } from '../redux/authSlice'

/** Sucursal en la que se trabaja: la eligen al ingresar y la cambian desde la barra superior. */
export function useActiveBranch() {
  const dispatch = useAppDispatch()
  const branch = useAppSelector(selectActiveBranch)
  const user = useAppSelector(selectCurrentUser)
  return {
    branch,
    branchId: branch?.id ?? null,
    branches: user?.branches ?? [],
    choose: (id: number) => dispatch(setActiveBranch(id)),
  }
}
