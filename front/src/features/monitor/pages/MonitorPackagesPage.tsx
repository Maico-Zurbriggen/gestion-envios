import { useDeferredValue, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  ChevronLeft,
  ChevronRight,
  Copy,
  Download,
  ExternalLink,
  FilterX,
  LoaderCircle,
  MapPin,
  PackageSearch,
  RefreshCw,
  Search,
  Truck,
  type LucideIcon,
} from 'lucide-react'
import { useAppSelector } from '../../../app/store'
import { FilterTabs, PageHeader } from '../../../shared/components/PageHeader'
import { showToast } from '../../../shared/services/toast'
import { selectAuthToken } from '../../auth/redux/authSlice'
import { useMonitorPackages, useMonitorSummary } from '../hooks/useMonitor'
import { exportMonitorPackages } from '../services/monitorApi'
import type { GroupFilter, MonitorFilters, MonitorOrder, MonitorPackage, MonitorSummary } from '../types/monitor.types'
import { formatDateTime, formatDay, formatRelative, GROUP_META } from '../utils/monitorFormat'

export interface PackagesSectionConfig {
  title: string
  description: string
  icon: LucideIcon
  /** Grupo fijo de la subsección; si hay pestañas, es la pestaña inicial. */
  group: GroupFilter
  tabs?: ReadonlyArray<{ id: GroupFilter; label: string }>
  empty: string
}

const PAGE_SIZES = [25, 50, 100]
const ORDER_LABELS: Record<MonitorOrder, string> = {
  movimiento: 'Último movimiento',
  recientes: 'Registrados recientemente',
  antiguos: 'Registrados hace más tiempo',
}

function tabCount(id: GroupFilter, summary: MonitorSummary | undefined) {
  if (!summary) return undefined
  if (id === 'TODOS') return summary.totalPackages
  if (id === 'CON_PROBLEMAS') return summary.withProblems
  if (id === 'SIN_RECORRIDO') return summary.withoutRoute
  if (id === 'CON_RECLAMO') return summary.withClaim
  return summary.byGroup[id] ?? 0
}

async function copy(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    showToast(`Copiado: ${text}`)
  } catch {
    showToast('No pudimos copiar el código.', 'error')
  }
}

export function MonitorPackagesPage({ config }: { config: PackagesSectionConfig }) {
  const token = useAppSelector(selectAuthToken)
  const [params, setParams] = useSearchParams()
  const [search, setSearch] = useState(() => params.get('q') ?? '')
  const deferredSearch = useDeferredValue(search)
  const [exporting, setExporting] = useState(false)
  const summary = useMonitorSummary().data

  const tabIds = config.tabs?.map((tab) => tab.id) ?? []
  const requestedGroup = params.get('grupo') as GroupFilter | null
  const group: GroupFilter = requestedGroup && tabIds.includes(requestedGroup) ? requestedGroup : config.group
  const filters: MonitorFilters = {
    search: deferredSearch,
    group,
    branchId: params.get('sucursal') ? Number(params.get('sucursal')) : null,
    deliveryType: (params.get('entrega') as MonitorFilters['deliveryType']) || null,
    from: params.get('desde'),
    to: params.get('hasta'),
    order: (params.get('orden') as MonitorOrder) || 'movimiento',
    page: Number(params.get('pagina')) || 1,
    pageSize: PAGE_SIZES.includes(Number(params.get('tam'))) ? Number(params.get('tam')) : 25,
  }
  const packagesQuery = useMonitorPackages(filters)
  const page = packagesQuery.data
  const filtersActive = Boolean(search.trim() || filters.branchId || filters.deliveryType || filters.from || filters.to)

  /** Cambia un filtro en la URL y vuelve a la primera página. */
  function setParam(key: string, value: string | null) {
    setParams(
      (current) => {
        const next = new URLSearchParams(current)
        if (value) next.set(key, value)
        else next.delete(key)
        if (key !== 'pagina') next.delete('pagina')
        return next
      },
      { replace: true },
    )
  }

  function clearFilters() {
    setSearch('')
    setParams((current) => {
      const next = new URLSearchParams()
      if (current.get('grupo')) next.set('grupo', current.get('grupo')!)
      return next
    }, { replace: true })
  }

  async function handleExport() {
    if (!token) return
    setExporting(true)
    try {
      const blob = await exportMonitorPackages(filters, token)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `paquetes-${new Date().toISOString().slice(0, 10)}.csv`
      link.click()
      URL.revokeObjectURL(url)
      showToast('Exportación lista. Se abre con Excel.')
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'No pudimos exportar.', 'error')
    } finally {
      setExporting(false)
    }
  }

  const first = page && page.total ? (page.page - 1) * page.pageSize + 1 : 0
  const last = page ? Math.min(page.page * page.pageSize, page.total) : 0

  return (
    <main className="monitor-page">
      <PageHeader
        icon={config.icon}
        eyebrow="Monitor de envíos"
        title={config.title}
        description={config.description}
        actions={
          <>
            <button className="btn" type="button" onClick={() => void packagesQuery.refetch()} disabled={packagesQuery.isFetching}>
              <RefreshCw size={17} className={packagesQuery.isFetching ? 'loading-icon' : undefined} aria-hidden="true" />
              Actualizar
            </button>
            <button className="btn btn--primary" type="button" onClick={() => void handleExport()} disabled={exporting || !page?.total}>
              {exporting ? <LoaderCircle className="loading-icon" size={17} aria-hidden="true" /> : <Download size={17} aria-hidden="true" />}
              Exportar CSV
            </button>
          </>
        }
      />

      {config.tabs ? (
        <FilterTabs<GroupFilter>
          label="Filtrar por etapa"
          value={group}
          onChange={(value) => setParam('grupo', value === config.group ? null : value)}
          tabs={config.tabs.map((tab) => ({ ...tab, count: tabCount(tab.id, summary) }))}
        />
      ) : null}

      <section className="list-card" aria-labelledby="monitor-list-title">
        <div className="list-toolbar monitor-toolbar">
          <h2 className="list-toolbar__title" id="monitor-list-title">
            Paquetes
            <small>{page ? `${page.total} ${page.total === 1 ? 'resultado' : 'resultados'}` : ''}</small>
          </h2>
          <div className="list-search monitor-toolbar__search">
            <Search size={16} aria-hidden="true" />
            <label className="visually-hidden" htmlFor="monitor-search">Buscar paquetes</label>
            <input
              id="monitor-search"
              type="search"
              placeholder="Paquete, código de seguimiento, persona, teléfono o destino"
              value={search}
              onChange={(event) => {
                setSearch(event.target.value)
                setParam('q', event.target.value.trim() || null)
              }}
            />
          </div>
          <div className="monitor-toolbar__filters">
            <label className="monitor-field">
              <span>Sucursal</span>
              <select className="list-select" value={filters.branchId ?? ''} onChange={(event) => setParam('sucursal', event.target.value || null)}>
                <option value="">Todas</option>
                {summary?.branches.map((branch) => (
                  <option key={branch.id} value={branch.id}>{branch.name}</option>
                ))}
              </select>
            </label>
            <label className="monitor-field">
              <span>Entrega</span>
              <select className="list-select" value={filters.deliveryType ?? ''} onChange={(event) => setParam('entrega', event.target.value || null)}>
                <option value="">Domicilio y sucursal</option>
                <option value="domicilio">A domicilio</option>
                <option value="sucursal">Retiro en sucursal</option>
              </select>
            </label>
            <label className="monitor-field">
              <span>Registrados desde</span>
              <input className="list-select" type="date" value={filters.from ?? ''} max={filters.to ?? undefined} onChange={(event) => setParam('desde', event.target.value || null)} />
            </label>
            <label className="monitor-field">
              <span>Hasta</span>
              <input className="list-select" type="date" value={filters.to ?? ''} min={filters.from ?? undefined} onChange={(event) => setParam('hasta', event.target.value || null)} />
            </label>
            <label className="monitor-field">
              <span>Ordenar por</span>
              <select className="list-select" value={filters.order} onChange={(event) => setParam('orden', event.target.value === 'movimiento' ? null : event.target.value)}>
                {Object.entries(ORDER_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </label>
            {filtersActive ? (
              <button className="btn btn--ghost monitor-toolbar__clear" type="button" onClick={clearFilters}>
                <FilterX size={16} aria-hidden="true" />
                Limpiar filtros
              </button>
            ) : null}
          </div>
        </div>

        {packagesQuery.isPending ? (
          <ul className="list-rows" aria-busy="true" aria-label="Cargando paquetes">
            {[0, 1, 2, 3, 4].map((item) => (
              <li className="list-row" key={item}>
                <span className="skeleton monitor-skeleton__icon" />
                <span className="monitor-skeleton__lines">
                  <span className="skeleton" />
                  <span className="skeleton" />
                </span>
              </li>
            ))}
          </ul>
        ) : packagesQuery.isError ? (
          <div className="list-empty" role="alert">
            <PackageSearch size={30} aria-hidden="true" />
            <strong>No pudimos cargar los paquetes</strong>
            <p>{packagesQuery.error.message}</p>
            <button className="btn" type="button" onClick={() => void packagesQuery.refetch()}>
              <RefreshCw size={16} aria-hidden="true" />
              Reintentar
            </button>
          </div>
        ) : !page?.packages.length ? (
          <div className="list-empty">
            <PackageSearch size={30} aria-hidden="true" />
            <strong>{filtersActive ? 'Ningún paquete coincide con los filtros' : 'No hay paquetes acá'}</strong>
            <p>{filtersActive ? 'Probá con otra búsqueda o quitá algún filtro.' : config.empty}</p>
          </div>
        ) : (
          <ul className={`list-rows ${packagesQuery.isFetching ? 'is-refreshing' : ''}`}>
            {page.packages.map((item) => (
              <PackageRow key={item.id} item={item} />
            ))}
          </ul>
        )}

        {page && page.total > 0 ? (
          <footer className="monitor-pagination">
            <span>
              {first}–{last} de {page.total}
            </span>
            <label className="monitor-pagination__size">
              <span>Por página</span>
              <select className="list-select" value={page.pageSize} onChange={(event) => setParam('tam', event.target.value === '25' ? null : event.target.value)}>
                {PAGE_SIZES.map((size) => (
                  <option key={size} value={size}>{size}</option>
                ))}
              </select>
            </label>
            <div className="monitor-pagination__nav">
              <button className="icon-action" type="button" aria-label="Página anterior" disabled={page.page <= 1} onClick={() => setParam('pagina', String(page.page - 1))}>
                <ChevronLeft size={18} aria-hidden="true" />
              </button>
              <span>
                Página {page.page} de {page.pages}
              </span>
              <button className="icon-action" type="button" aria-label="Página siguiente" disabled={page.page >= page.pages} onClick={() => setParam('pagina', String(page.page + 1))}>
                <ChevronRight size={18} aria-hidden="true" />
              </button>
            </div>
          </footer>
        ) : null}
      </section>
    </main>
  )
}

function PackageRow({ item }: { item: MonitorPackage }) {
  const meta = GROUP_META[item.group]
  const Icon = meta.icon
  const traceUrl = `/monitor/trazabilidad/${item.code}`
  return (
    <li className={`list-row monitor-row tone-${meta.tone}`}>
      <span className="monitor-row__icon" aria-hidden="true">
        <Icon size={18} />
      </span>
      <div className="list-row__main">
        <p className="list-row__title">
          <Link className="monitor-row__code" to={traceUrl}>
            {item.code}
          </Link>
          <span className={`badge monitor-badge tone-${meta.tone}`}>{item.statusLabel}</span>
          {item.withoutRoute ? <span className="badge badge--warning">Sin recorrido</span> : null}
          {item.failedAttempts ? (
            <span className="badge badge--danger">
              {item.failedAttempts} {item.failedAttempts === 1 ? 'visita fallida' : 'visitas fallidas'}
            </span>
          ) : null}
          {item.activeClaims ? (
            <span className="badge badge--warning">
              {item.activeClaims} {item.activeClaims === 1 ? 'reclamo' : 'reclamos'}
            </span>
          ) : null}
        </p>
        <p className="list-row__meta">
          <span>{item.description}</span>
          <span>{item.weightKg} kg</span>
          <span className="monitor-row__token">{item.trackingToken}</span>
        </p>
        <p className="list-row__meta monitor-row__route">
          <span>
            De {item.senderName} para <strong>{item.recipientName}</strong>
          </span>
          <span>
            <MapPin size={12} aria-hidden="true" />
            {item.deliveryType === 'domicilio' ? 'Domicilio: ' : ''}
            {item.destination}
          </span>
          {item.currentBranch ? <span>Ubicado en {item.currentBranch}</span> : null}
          {item.route ? (
            <span>
              <Truck size={12} aria-hidden="true" />
              {item.route.driverName} · {formatDay(item.route.date)} · parada {item.route.stop}
            </span>
          ) : null}
        </p>
      </div>
      <div className="monitor-row__aside">
        <span className="monitor-row__time" title={formatDateTime(item.updatedAt)}>
          {formatRelative(item.updatedAt)}
        </span>
        <div className="list-row__aside">
          <button className="icon-action" type="button" title="Copiar número de paquete" aria-label={`Copiar ${item.code}`} onClick={() => void copy(item.code)}>
            <Copy size={16} aria-hidden="true" />
          </button>
          <a
            className="icon-action"
            href={`/seguimiento?token=${item.trackingToken}`}
            target="_blank"
            rel="noreferrer"
            title="Ver el seguimiento público"
            aria-label={`Ver el seguimiento público de ${item.code}`}
          >
            <ExternalLink size={16} aria-hidden="true" />
          </a>
          <Link className="icon-action icon-action--primary" to={traceUrl} title="Ver trazabilidad" aria-label={`Ver la trazabilidad de ${item.code}`}>
            <PackageSearch size={17} aria-hidden="true" />
          </Link>
        </div>
      </div>
    </li>
  )
}
