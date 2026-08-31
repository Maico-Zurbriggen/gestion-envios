import { useEffect, useState } from 'react'
import {
  LogOut,
  Menu,
  Moon,
  PackageCheck,
  Sun,
  UserPlus,
  X,
} from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAppDispatch, useAppSelector } from '../../app/store'
import {
  clearCredentials,
  selectCurrentUser,
} from '../../features/auth/redux/authSlice'
import { useTheme } from '../../shared/hooks/useTheme'
import './MainLayout.css'

export function MainLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const user = useAppSelector(selectCurrentUser)
  const dispatch = useAppDispatch()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { theme, toggleTheme } = useTheme()

  useEffect(() => {
    if (!sidebarOpen) return

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setSidebarOpen(false)
    }

    const isCompactViewport = window.matchMedia('(max-width: 968px)').matches
    if (isCompactViewport) document.body.style.overflow = 'hidden'
    window.addEventListener('keydown', handleKeyDown)

    return () => {
      document.body.style.overflow = ''
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [sidebarOpen])

  function handleLogout() {
    queryClient.clear()
    dispatch(clearCredentials())
    navigate('/login', { replace: true })
  }

  return (
    <div className="app-layout">
      <button
        className={`sidebar-backdrop ${sidebarOpen ? 'is-visible' : ''}`}
        type="button"
        aria-label="Cerrar menú de navegación"
        tabIndex={sidebarOpen ? 0 : -1}
        onClick={() => setSidebarOpen(false)}
      />

      <aside
        className={`app-sidebar ${sidebarOpen ? 'is-open' : ''}`}
        id="main-navigation"
        aria-label="Navegación principal"
      >
        <header className="sidebar-header">
          <NavLink
            className="sidebar-brand"
            to="/"
            onClick={() => setSidebarOpen(false)}
          >
            <span className="sidebar-brand__mark" aria-hidden="true">
              <PackageCheck size={23} />
            </span>
            <span>
              <strong>Gestión</strong>
              <small>de envíos</small>
            </span>
          </NavLink>
          <button
            className="sidebar-close"
            type="button"
            aria-label="Cerrar menú"
            onClick={() => setSidebarOpen(false)}
          >
            <X size={21} aria-hidden="true" />
          </button>
        </header>

        <nav className="sidebar-nav">
          <span className="sidebar-nav__label">Administración</span>
          {user?.role === 'SUPERADMIN' && (
            <NavLink
              className={({ isActive }) =>
                `sidebar-nav__item ${isActive ? 'is-active' : ''}`
              }
              to="/admin/usuarios/nuevo"
              onClick={() => setSidebarOpen(false)}
            >
              <UserPlus size={19} aria-hidden="true" />
              Registrar usuario
            </NavLink>
          )}
        </nav>

        <footer className="sidebar-footer">
          <div className="sidebar-user">
            <span className="sidebar-user__avatar" aria-hidden="true">
              {(user?.name || user?.dni || 'U').slice(0, 1).toUpperCase()}
            </span>
            <span className="sidebar-user__details">
              <strong>{user?.name || `Usuario ${user?.dni ?? ''}`}</strong>
              <small>{user?.role || 'Sin rol asignado'}</small>
            </span>
          </div>

          <button className="sidebar-action" type="button" onClick={toggleTheme}>
            {theme === 'light' ? (
              <Moon size={19} aria-hidden="true" />
            ) : (
              <Sun size={19} aria-hidden="true" />
            )}
            {theme === 'light' ? 'Usar tema oscuro' : 'Usar tema claro'}
          </button>

          <button
            className="sidebar-action sidebar-action--danger"
            type="button"
            onClick={handleLogout}
          >
            <LogOut size={19} aria-hidden="true" />
            Cerrar sesión
          </button>
        </footer>
      </aside>

      <div className="app-content">
        <header className="mobile-header">
          <button
            className="mobile-menu-button"
            type="button"
            aria-label="Abrir menú de navegación"
            aria-controls="main-navigation"
            aria-expanded={sidebarOpen}
            onClick={() => setSidebarOpen(true)}
          >
            <Menu size={22} aria-hidden="true" />
          </button>
          <span>Gestión de envíos</span>
        </header>
        <div className="app-content__body">
          <Outlet />
        </div>
      </div>
    </div>
  )
}
