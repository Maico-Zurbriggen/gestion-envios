import { ChevronRight, MonitorDot } from 'lucide-react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { isChildActive, NAVIGATION_MODULES } from '../../../app/navigation'
import { useMonitorSummary } from '../hooks/useMonitor'
import { countForSection } from '../utils/monitorFormat'
import '../monitor.css'

const MONITOR = NAVIGATION_MODULES.find((module) => module.id === 'monitor')!

/** Marco común de las subsecciones del monitor: migas y barra de subsecciones. */
export function MonitorLayout() {
  const { pathname } = useLocation()
  const summary = useMonitorSummary().data
  const children = MONITOR.children ?? []
  const current = children.find((child) => isChildActive(child, MONITOR, pathname))

  return (
    <div className="monitor-area">
      <nav className="monitor-breadcrumb" aria-label="Ubicación">
        <Link to={MONITOR.path}>
          <MonitorDot size={14} aria-hidden="true" />
          Monitor
        </Link>
        {current && current.path !== MONITOR.path ? (
          <>
            <ChevronRight size={14} aria-hidden="true" />
            <span aria-current="page">{current.label}</span>
          </>
        ) : null}
      </nav>

      <nav className="monitor-subnav" aria-label="Secciones del monitor">
        {children.map((child) => {
          const Icon = child.icon
          const active = isChildActive(child, MONITOR, pathname)
          const count = countForSection(child.id, summary)
          const alert = (child.id === 'monitor-incidents' || child.id === 'monitor-claims') && Boolean(count)
          return (
            <NavLink
              key={child.id}
              to={child.path}
              end
              className={`monitor-subnav__item ${active ? 'is-active' : ''}`}
              aria-current={active ? 'page' : undefined}
            >
              <Icon size={15} aria-hidden="true" />
              <span>{child.label}</span>
              {count !== undefined ? (
                <span className={`monitor-subnav__count ${alert ? 'is-alert' : ''}`}>{count}</span>
              ) : null}
            </NavLink>
          )
        })}
      </nav>

      <Outlet />
    </div>
  )
}
