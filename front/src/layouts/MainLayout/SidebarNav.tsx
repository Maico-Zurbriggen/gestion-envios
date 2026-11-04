import { AnimatePresence, LayoutGroup, LazyMotion, m } from 'framer-motion'
import { ChevronDown } from 'lucide-react'
import { NavLink, useNavigate } from 'react-router-dom'
import { isChildActive, NAVIGATION_SECTIONS, type NavigationModule } from '../../app/navigation'

/** La misma curva y el mismo resorte que Aviso Entrega, TamboApp y Sodería: es la firma de las apps. */
const ease = [0.16, 1, 0.3, 1] as const
const indicatorSpring = { type: 'spring', stiffness: 500, damping: 40 } as const
const instant = { duration: 0 } as const
const loadMotionFeatures = () => import('./motionFeatures').then((module) => module.default)

interface SidebarNavProps {
  modules: NavigationModule[]
  pathname: string
  collapsed: boolean
  /** Justo después de colapsar o expandir, el resaltado aparece en su lugar sin viajar. */
  instantIndicator: boolean
  openGroups: Record<string, boolean>
  onToggleGroup: (id: string, open: boolean) => void
  onNavigate: () => void
}

function inModule(module: NavigationModule, pathname: string) {
  return module.path === '/' ? pathname === '/' : pathname === module.path || pathname.startsWith(`${module.path}/`)
}

/** Bloque de color que marca la sección activa y se desliza de una a otra. */
function ActiveIndicator({ instantIndicator }: { instantIndicator: boolean }) {
  return <m.span layoutId="sidebar-active" className="nav-active-indicator" transition={instantIndicator ? instant : indicatorSpring} />
}

export function SidebarNav({ modules, pathname, collapsed, instantIndicator, openGroups, onToggleGroup, onNavigate }: SidebarNavProps) {
  const navigate = useNavigate()

  return (
    <LazyMotion features={loadMotionFeatures} strict>
      <nav className="sidebar-nav" aria-label="Secciones">
        <LayoutGroup id="sidebar">
          {NAVIGATION_SECTIONS.map((group) => {
            const groupModules = modules.filter((module) => module.section === group.id)
            if (!groupModules.length) return null
            return (
              <div className="nav-group" key={group.id}>
                <div className="nav-group-label"><p>{group.label}</p><span aria-hidden="true" /></div>
                <ul>
                  {groupModules.map((module) => {
                    const Icon = module.icon
                    const children = module.children ?? []
                    const current = inModule(module, pathname)

                    if (!children.length) {
                      return (
                        <li className="nav-section" key={module.id}>
                          <NavLink
                            to={module.path}
                            end={module.path === '/'}
                            className={`nav-section-trigger${current ? ' active filled' : ''}`}
                            title={collapsed ? module.label : undefined}
                            aria-label={collapsed ? module.label : undefined}
                            onClick={onNavigate}
                          >
                            {current && <ActiveIndicator instantIndicator={instantIndicator} />}
                            <span className="nav-section-title">
                              <Icon size={18} strokeWidth={1.8} aria-hidden="true" />
                              <span className="nav-label">{module.label}</span>
                            </span>
                          </NavLink>
                        </li>
                      )
                    }

                    const activeChild = children.find((child) => isChildActive(child, module, pathname))
                    const expanded = !collapsed && (openGroups[module.id] ?? current)
                    // Con la barra colapsada o sin subsección activa, el resaltado queda en la sección.
                    const filled = current && (collapsed || !activeChild)
                    const listId = `sidebar-${module.id}`
                    return (
                      <li className={`nav-section${expanded ? ' expanded' : ''}`} key={module.id}>
                        <button
                          type="button"
                          className={`nav-section-trigger${current ? ' active' : ''}${filled ? ' filled' : ''}`}
                          title={collapsed ? module.label : undefined}
                          aria-label={collapsed ? module.label : undefined}
                          aria-expanded={collapsed ? undefined : expanded}
                          aria-controls={collapsed ? undefined : listId}
                          onClick={() => {
                            if (current && expanded) return onToggleGroup(module.id, false)
                            onToggleGroup(module.id, true)
                            if (!current || collapsed) {
                              navigate(module.path)
                              onNavigate()
                            }
                          }}
                        >
                          {filled && <ActiveIndicator instantIndicator={instantIndicator} />}
                          <span className="nav-section-title">
                            <Icon size={18} strokeWidth={1.8} aria-hidden="true" />
                            <span className="nav-label">{module.label}</span>
                          </span>
                          <ChevronDown className="nav-section-chevron" size={16} aria-hidden="true" />
                        </button>
                        <AnimatePresence initial={false}>
                          {expanded && (
                            <m.ul
                              id={listId}
                              className="nav-section-children"
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: 'auto', opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              transition={{ duration: 0.22, ease }}
                            >
                              {children.map((child) => {
                                const ChildIcon = child.icon
                                const active = child === activeChild
                                return (
                                  <li key={child.id}>
                                    <NavLink
                                      to={child.path}
                                      end
                                      className={active ? 'active' : undefined}
                                      aria-current={active ? 'page' : undefined}
                                      onClick={onNavigate}
                                    >
                                      {active && <ActiveIndicator instantIndicator={instantIndicator} />}
                                      <ChildIcon size={16} strokeWidth={1.8} aria-hidden="true" />
                                      <span>{child.label}</span>
                                    </NavLink>
                                  </li>
                                )
                              })}
                            </m.ul>
                          )}
                        </AnimatePresence>
                      </li>
                    )
                  })}
                </ul>
              </div>
            )
          })}
        </LayoutGroup>
      </nav>
    </LazyMotion>
  )
}
