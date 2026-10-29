import type { ReactNode } from 'react'
import { ChevronDown, SlidersHorizontal } from 'lucide-react'

interface CollapsibleFilterSectionProps {
  title: string
  description?: string
  /** Resumen de lo aplicado, visible aunque el panel esté cerrado. */
  status?: ReactNode
  sticky?: boolean
  defaultOpen?: boolean
  contentClassName?: string
  children: ReactNode
}

/**
 * Panel de filtros plegable, como el de TamboApp: muestra un resumen de lo
 * aplicado y se despliega para cambiarlo. Usa `<details>`, así que funciona
 * con teclado y lector de pantalla sin código extra.
 */
export function CollapsibleFilterSection({
  title,
  description,
  status,
  sticky = false,
  defaultOpen = false,
  contentClassName = '',
  children,
}: CollapsibleFilterSectionProps) {
  return (
    <details className={`filter-panel ${sticky ? 'filter-panel--sticky' : ''}`} open={defaultOpen || undefined}>
      <summary>
        <span className="filter-panel__icon" aria-hidden="true">
          <SlidersHorizontal size={16} />
        </span>
        <span className="filter-panel__heading">
          <strong>{title}</strong>
          {description ? <small>{description}</small> : null}
        </span>
        <span className="filter-panel__actions">
          {status ? <span className="filter-panel__status">{status}</span> : null}
          <span className="filter-panel__toggle" aria-hidden="true">
            <span className="filter-panel__show">Mostrar</span>
            <span className="filter-panel__hide">Ocultar</span>
            <ChevronDown size={14} />
          </span>
        </span>
      </summary>
      <div className={`filter-panel__content ${contentClassName}`.trim()}>{children}</div>
    </details>
  )
}
