import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'

interface PageHeaderProps {
  icon: LucideIcon
  title: string
  description?: ReactNode
  eyebrow?: string
  actions?: ReactNode
}

/** Encabezado común de las pantallas del panel: ícono, título, descripción y acciones. */
export function PageHeader({ icon: Icon, title, description, eyebrow, actions }: PageHeaderProps) {
  return (
    <header className="page-header">
      <span className="page-header__icon" aria-hidden="true">
        <Icon size={22} />
      </span>
      <div className="page-header__titles">
        {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
        <h1>{title}</h1>
        {description ? <p className="page-header__description">{description}</p> : null}
      </div>
      {actions ? <div className="page-header__actions">{actions}</div> : null}
    </header>
  )
}

interface StatCardProps {
  label: string
  value: ReactNode
  icon: LucideIcon
  tone?: 'brand' | 'success' | 'muted' | 'info'
  hint?: string
}

export function StatCard({ label, value, icon: Icon, tone = 'brand', hint }: StatCardProps) {
  return (
    <div className={`stat-card stat-card--${tone}`}>
      <div>
        <p className="stat-card__label">{label}</p>
        <p className="stat-card__value">{value}</p>
        {hint ? <p className="stat-card__hint">{hint}</p> : null}
      </div>
      <span className="stat-card__icon" aria-hidden="true">
        <Icon size={20} />
      </span>
    </div>
  )
}

interface FilterTab<T extends string> {
  id: T
  label: string
  count?: number
  icon?: LucideIcon
}

interface FilterTabsProps<T extends string> {
  label: string
  tabs: ReadonlyArray<FilterTab<T>>
  value: T
  onChange: (value: T) => void
}

/** Filtros en forma de pestañas con contador, como las tarjetas de Aviso Entrega. */
export function FilterTabs<T extends string>({ label, tabs, value, onChange }: FilterTabsProps<T>) {
  return (
    <div className="filter-tabs" role="tablist" aria-label={label}>
      {tabs.map(({ id, label: tabLabel, count, icon: Icon }) => (
        <button
          key={id}
          className={`filter-tab ${value === id ? 'is-active' : ''}`}
          type="button"
          role="tab"
          aria-selected={value === id}
          onClick={() => onChange(id)}
        >
          {Icon ? <Icon size={16} aria-hidden="true" /> : null}
          <span>{tabLabel}</span>
          {count !== undefined ? <span className="filter-tab__count">{count}</span> : null}
        </button>
      ))}
    </div>
  )
}
