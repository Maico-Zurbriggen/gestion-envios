import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAppSelector } from '../app/store'
import {
  selectCurrentUser,
  selectIsAuthenticated,
  type UserRole,
} from '../features/auth/redux/authSlice'

interface ProtectedRoutesProps {
  allowedRoles?: readonly UserRole[]
}

export function ProtectedRoutes({ allowedRoles }: ProtectedRoutesProps) {
  const location = useLocation()
  const isAuthenticated = useAppSelector(selectIsAuthenticated)
  const user = useAppSelector(selectCurrentUser)

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  const hasRequiredRole =
    !allowedRoles?.length ||
    allowedRoles.some((allowedRole) => user?.roles.includes(allowedRole))

  if (!hasRequiredRole) {
    return <Navigate to="/unauthorized" replace />
  }

  return <Outlet />
}
