import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAppSelector } from '../app/store'
import { requiresBranch } from '../features/auth/branchAccess'
import {
  selectActiveBranchId,
  selectCurrentUser,
  selectIsAuthenticated,
} from '../features/auth/redux/authSlice'

interface ProtectedRoutesProps {
  allowedRoles?: readonly string[]
  /** Por defecto toda ruta privada trabaja sobre una sucursal elegida. */
  requireBranch?: boolean
}

export function ProtectedRoutes({ allowedRoles, requireBranch = true }: ProtectedRoutesProps) {
  const location = useLocation()
  const isAuthenticated = useAppSelector(selectIsAuthenticated)
  const user = useAppSelector(selectCurrentUser)
  const activeBranchId = useAppSelector(selectActiveBranchId)

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  const hasRequiredRole =
    !allowedRoles?.length ||
    allowedRoles.includes(user?.role ?? '')

  if (!hasRequiredRole) {
    return <Navigate to="/unauthorized" replace />
  }

  if (requireBranch && requiresBranch(user?.role) && activeBranchId === null) {
    return <Navigate to="/elegir-sucursal" replace state={{ from: location }} />
  }

  return <Outlet />
}
