import { useEffect, useState } from 'react'
import {
  ChevronsLeft,
  ChevronsRight,
  KeyRound,
  LogOut,
  Menu,
  Moon,
  MoreHorizontal,
  PackageCheck,
  PanelLeft,
  Search,
  Sun,
  X,
} from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAppDispatch, useAppSelector } from '../../app/store'
import { getAccessibleModules, NAVIGATION_SECTIONS } from '../../app/navigation'
import { SidebarGroup } from './SidebarGroup'
import { clearCredentials, selectCurrentUser } from '../../features/auth/redux/authSlice'
import { BranchSwitcher } from './BranchSwitcher'
import { Toaster } from '../../shared/components/Toaster'
import { useTheme } from '../../shared/hooks/useTheme'
import { initials, roleLabel } from '../../shared/utils/roles'
import { CommandPalette, type CommandItem } from './CommandPalette'
import { PanelLayoutContext } from './panelContext'
import { readSidebarCollapsed, storeSidebarCollapsed, useApiStatus, useNow } from './useLayoutStatus'
import './MainLayout.css'

const timeFormatter = new Intl.DateTimeFormat('es-AR', { hour: '2-digit', minute: '2-digit' })
const dayFormatter = new Intl.DateTimeFormat('es-AR', { weekday: 'long', day: 'numeric', month: 'short' })

function isTypingTarget(target: EventTarget | null) {
  return target instanceof HTMLElement && (target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName))
}

export function MainLayout() {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(readSidebarCollapsed)
  const [paletteOpen, setPaletteOpen] = useState(false)
  // Grupos que la persona abrió o cerró a mano; si no tocó nada, se abre el de la ruta actual.
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({})
  const location = useLocation()
  const user = useAppSelector(selectCurrentUser)
  const dispatch = useAppDispatch()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { theme, setTheme, toggleTheme } = useTheme()
  const apiStatus = useApiStatus()
  const now = useNow()
  const accessibleModules = getAccessibleModules(user?.role)
  const displayName = user?.name || `Usuario ${user?.dni ?? ''}`.trim()
  const roleName = user?.role ? roleLabel(user.role) : 'Sin rol asignado'
  // En el celular: las primeras cuatro secciones abajo y el resto en «Más».
  const bottomModules = accessibleModules.slice(0, 4)

  useEffect(() => {
    if (!drawerOpen) return
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setDrawerOpen(false)
    }
    document.body.style.overflow = 'hidden'
    window.addEventListener('keydown', handleKeyDown)
    return () => {
      document.body.style.overflow = ''
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [drawerOpen])

  useEffect(() => {
    function handleShortcut(event: KeyboardEvent) {
      const opensWithModifier = (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k'
      const opensWithSlash = event.key === '/' && !isTypingTarget(event.target)
      if (!opensWithModifier && !opensWithSlash) return
      event.preventDefault()
      setDrawerOpen(false)
      setPaletteOpen(true)
    }
    window.addEventListener('keydown', handleShortcut)
    return () => window.removeEventListener('keydown', handleShortcut)
  }, [])

  function toggleCollapsed() {
    setCollapsed((current) => {
      storeSidebarCollapsed(!current)
      return !current
    })
  }

  function handleLogout() {
    queryClient.clear()
    dispatch(clearCredentials())
    navigate('/login', { replace: true })
  }

  const commands: CommandItem[] = [
    ...accessibleModules.map((module) => ({
      id: module.id,
      label: module.label,
      description: module.description,
      icon: module.icon,
      group: NAVIGATION_SECTIONS.find((section) => section.id === module.section)?.label ?? 'Secciones',
      keywords: module.keywords,
      run: () => navigate(module.path),
    })),
    ...accessibleModules.flatMap((module) =>
      (module.children ?? [])
        .filter((child) => child.path !== module.path)
        .map((child) => ({
          id: child.id,
          label: child.label,
          description: child.description,
          icon: child.icon,
          group: module.label,
          keywords: child.keywords,
          run: () => navigate(child.path),
        })),
    ),
    {
      id: 'theme',
      label: theme === 'light' ? 'Usar tema oscuro' : 'Usar tema claro',
      description: 'Cambia los colores de toda la aplicación.',
      icon: theme === 'light' ? Moon : Sun,
      group: 'Acciones',
      keywords: 'modo noche dia apariencia',
      run: toggleTheme,
    },
    {
      id: 'collapse',
      label: collapsed ? 'Expandir menú lateral' : 'Colapsar menú lateral',
      description: 'Deja más espacio para el contenido en pantallas grandes.',
      icon: PanelLeft,
      group: 'Acciones',
      keywords: 'barra sidebar',
      run: toggleCollapsed,
    },
    {
      id: 'password',
      label: 'Cambiar mi contraseña',
      description: 'Elegí una contraseña nueva para tu cuenta.',
      icon: KeyRound,
      group: 'Acciones',
      keywords: 'clave seguridad',
      run: () => navigate('/cambiar-password'),
    },
    {
      id: 'logout',
      label: 'Cerrar sesión',
      description: 'Salí de tu cuenta en este dispositivo.',
      icon: LogOut,
      group: 'Acciones',
      keywords: 'salir logout',
      run: handleLogout,
    },
  ]

  const apiState = apiStatus.isPending ? 'checking' : apiStatus.data ? 'online' : 'offline'
  const apiLabel = { checking: 'Conectando…', online: 'En línea', offline: 'Sin conexión' }[apiState]

  return (
    <div className={`app-layout ${collapsed ? 'is-collapsed' : ''}`}>
      <button
        className={`sidebar-backdrop ${drawerOpen ? 'is-visible' : ''}`}
        type="button"
        aria-label="Cerrar menú de navegación"
        tabIndex={drawerOpen ? 0 : -1}
        onClick={() => setDrawerOpen(false)}
      />

      <aside className={`app-sidebar ${drawerOpen ? 'is-open' : ''}`} id="main-navigation" aria-label="Navegación principal">
        <header className="sidebar-header">
          <NavLink className="sidebar-brand" to="/" title="Gestión de envíos" onClick={() => setDrawerOpen(false)}>
            <span className="sidebar-brand__mark" aria-hidden="true">
              <PackageCheck size={20} />
            </span>
            <span className="sidebar-brand__text">
              <strong>Gestión de envíos</strong>
              <small>y distribución</small>
            </span>
          </NavLink>
          <button className="sidebar-close" type="button" aria-label="Cerrar menú" onClick={() => setDrawerOpen(false)}>
            <X size={20} aria-hidden="true" />
          </button>
        </header>

        <nav className="sidebar-nav">
          {NAVIGATION_SECTIONS.map((section) => {
            const sectionModules = accessibleModules.filter((module) => module.section === section.id)
            if (!sectionModules.length) return null
            return (
              <div className="sidebar-nav__section" key={section.id}>
                <span className="sidebar-nav__label">
                  <span>{section.label}</span>
                </span>
                {sectionModules.map((module) => {
                  const Icon = module.icon
                  if (module.children?.length) {
                    return (
                      <SidebarGroup
                        key={module.id}
                        module={module}
                        collapsed={collapsed}
                        pathname={location.pathname}
                        expanded={openGroups[module.id] ?? location.pathname.startsWith(module.path)}
                        onToggle={(open) => setOpenGroups((current) => ({ ...current, [module.id]: open }))}
                        onNavigate={() => setDrawerOpen(false)}
                      />
                    )
                  }
                  return (
                    <NavLink
                      className={({ isActive }) => `sidebar-nav__item ${isActive ? 'is-active' : ''}`}
                      end={module.path === '/'}
                      key={module.id}
                      to={module.path}
                      title={collapsed ? module.label : undefined}
                      onClick={() => setDrawerOpen(false)}
                    >
                      <Icon size={18} aria-hidden="true" />
                      <span className="sidebar-nav__text">{module.label}</span>
                    </NavLink>
                  )
                })}
              </div>
            )
          })}
        </nav>

        <footer className="sidebar-footer">
          <button
            className="sidebar-collapse"
            type="button"
            aria-pressed={collapsed}
            title={collapsed ? 'Expandir menú' : 'Colapsar menú'}
            onClick={toggleCollapsed}
          >
            {collapsed ? <ChevronsRight size={18} aria-hidden="true" /> : <ChevronsLeft size={18} aria-hidden="true" />}
            <span className="sidebar-nav__text">{collapsed ? 'Expandir' : 'Colapsar'}</span>
          </button>
        </footer>
      </aside>

      <div className="app-content">
        <header className="app-topbar">
          <button
            className="topbar-icon-button topbar-menu"
            type="button"
            aria-label="Abrir menú de navegación"
            aria-controls="main-navigation"
            aria-expanded={drawerOpen}
            onClick={() => setDrawerOpen(true)}
          >
            <Menu size={20} aria-hidden="true" />
          </button>

          <div className="topbar-user">
            <span className="topbar-user__avatar" aria-hidden="true">
              {initials(displayName)}
            </span>
            <span className="topbar-user__details">
              <strong>{displayName}</strong>
              <small>{user?.email || `DNI ${user?.dni ?? ''}`}</small>
            </span>
            <span className="badge topbar-user__role">{roleName}</span>
          </div>

          <BranchSwitcher />

          <button className="topbar-search" type="button" onClick={() => setPaletteOpen(true)} aria-keyshortcuts="Control+K">
            <Search size={16} aria-hidden="true" />
            <span>Buscar o ir a…</span>
            <kbd>Ctrl K</kbd>
          </button>

          <div className="topbar-tools">
            <span className="topbar-clock" aria-label={`Hora actual ${timeFormatter.format(now)}`}>
              <strong>{timeFormatter.format(now)}</strong>
              <small>{dayFormatter.format(now)}</small>
            </span>
            <span className={`topbar-status topbar-status--${apiState}`} title="Estado del servidor" role="status">
              <span className="topbar-status__dot" aria-hidden="true" />
              <span className="topbar-status__text">{apiLabel}</span>
            </span>
            <div className="segmented topbar-theme" role="group" aria-label="Tema de colores">
              <button type="button" aria-pressed={theme === 'light'} onClick={() => setTheme('light')}>
                <Sun size={15} aria-hidden="true" />
                <span>Claro</span>
              </button>
              <button type="button" aria-pressed={theme === 'dark'} onClick={() => setTheme('dark')}>
                <Moon size={15} aria-hidden="true" />
                <span>Oscuro</span>
              </button>
            </div>
            <button
              className="topbar-icon-button topbar-theme-compact"
              type="button"
              aria-label={theme === 'light' ? 'Usar tema oscuro' : 'Usar tema claro'}
              onClick={toggleTheme}
            >
              {theme === 'light' ? <Moon size={18} aria-hidden="true" /> : <Sun size={18} aria-hidden="true" />}
            </button>
            <button className="topbar-logout" type="button" onClick={handleLogout} aria-label="Cerrar sesión">
              <LogOut size={17} aria-hidden="true" />
              <span>Salir</span>
            </button>
          </div>
        </header>

        <div className="app-content__body">
          <PanelLayoutContext.Provider value={true}>
            <Outlet />
          </PanelLayoutContext.Provider>
        </div>
      </div>

      <nav className="bottom-nav" aria-label="Accesos rápidos">
        {bottomModules.map((module) => {
          const Icon = module.icon
          return (
            <NavLink
              key={module.id}
              className={({ isActive }) => `bottom-nav__item ${isActive ? 'is-active' : ''}`}
              to={module.path}
              end={module.path === '/'}
            >
              <Icon size={20} aria-hidden="true" />
              <span>{module.shortLabel}</span>
            </NavLink>
          )
        })}
        <button className="bottom-nav__item" type="button" aria-controls="main-navigation" aria-expanded={drawerOpen} onClick={() => setDrawerOpen(true)}>
          <MoreHorizontal size={20} aria-hidden="true" />
          <span>Más</span>
        </button>
      </nav>

      <CommandPalette open={paletteOpen} items={commands} onClose={() => setPaletteOpen(false)} />
      <Toaster />
    </div>
  )
}
