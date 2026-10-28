import { useId } from 'react'
import { ChevronDown } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { isChildActive, type NavigationModule } from '../../app/navigation'

interface SidebarGroupProps {
  module: NavigationModule
  collapsed: boolean
  pathname: string
  expanded: boolean
  onToggle: (open: boolean) => void
  onNavigate: () => void
}

/**
 * Sección general con subsecciones, como en TamboApp: el título lleva a la
 * portada y despliega la lista; la subsección activa queda resaltada.
 * Con el menú colapsado solo queda el ícono de la sección.
 */
export function SidebarGroup({ module, collapsed, pathname, expanded, onToggle, onNavigate }: SidebarGroupProps) {
  const listId = useId()
  const Icon = module.icon
  const inSection = pathname === module.path || pathname.startsWith(`${module.path}/`)
  const open = expanded && !collapsed
  const children = module.children ?? []

  return (
    <div className={`sidebar-group ${open ? 'is-expanded' : ''}`}>
      <div className="sidebar-group__head">
        <NavLink
          className={`sidebar-nav__item sidebar-group__trigger ${inSection ? (collapsed ? 'is-active' : 'is-current') : ''}`}
          to={module.path}
          end
          title={collapsed ? module.label : undefined}
          aria-current={pathname === module.path ? 'page' : undefined}
          onClick={() => {
            onToggle(true)
            onNavigate()
          }}
        >
          <Icon size={18} aria-hidden="true" />
          <span className="sidebar-nav__text">{module.label}</span>
        </NavLink>
        {!collapsed ? (
          <button
            className="sidebar-group__toggle"
            type="button"
            aria-expanded={open}
            aria-controls={listId}
            aria-label={`${open ? 'Ocultar' : 'Mostrar'} las secciones de ${module.label}`}
            onClick={() => onToggle(!open)}
          >
            <ChevronDown size={16} aria-hidden="true" />
          </button>
        ) : null}
      </div>
      {open ? (
        <ul className="sidebar-subnav" id={listId}>
          {children.map((child) => {
            const ChildIcon = child.icon
            const active = isChildActive(child, module, pathname)
            return (
              <li key={child.id}>
                <NavLink
                  className={`sidebar-subnav__item ${active ? 'is-active' : ''}`}
                  to={child.path}
                  end
                  aria-current={active ? 'page' : undefined}
                  onClick={onNavigate}
                >
                  <ChildIcon size={15} aria-hidden="true" />
                  <span>{child.label}</span>
                </NavLink>
              </li>
            )
          })}
        </ul>
      ) : null}
    </div>
  )
}
