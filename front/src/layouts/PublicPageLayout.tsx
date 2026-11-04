import { Outlet } from 'react-router-dom'
import { useAppSelector } from '../app/store'
import { selectIsAuthenticated } from '../features/auth/redux/authSlice'
import { MainLayout } from './MainLayout/MainLayout'

/**
 * Páginas públicas (registro, seguimiento, sucursales, preguntas frecuentes).
 * Un cliente las ve sueltas; el personal con sesión las ve dentro del panel,
 * para no perder el menú lateral al navegar entre secciones.
 */
export function PublicPageLayout() {
  const isAuthenticated = useAppSelector(selectIsAuthenticated)
  return isAuthenticated ? <MainLayout /> : <Outlet />
}
