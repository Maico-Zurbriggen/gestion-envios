import { useRef, useState, type CSSProperties, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  ArrowLeft,
  CheckCircle2,
  CircleAlert,
  ClipboardCheck,
  Clock3,
  LoaderCircle,
  Lock,
  PackageCheck,
  PackageSearch,
  PackageX,
  RefreshCw,
  ScanBarcode,
  Truck,
} from 'lucide-react'
import { Modal } from '../../../shared/components/Modal'
import { FilterTabs, PageHeader } from '../../../shared/components/PageHeader'
import { ScanWithCameraButton } from '../../../shared/components/ScanWithCameraButton'
import { PACKAGE_CODE_PATTERN } from '../../../shared/services/scannedCode'
import { showToast } from '../../../shared/services/toast'
import { ActiveBranchNote } from '../../auth/components/ActiveBranchNote'
import { useActiveBranch } from '../../auth/hooks/useActiveBranch'
import { useRoutesToControl, useUnloadControl, useUnloadMutations } from '../hooks/useUnload'
import type { ControlType, IncomingRoute, ReadOutcome, UnloadControl } from '../services/unloadApi'
import './UnloadControlPage.css'

const dayFormatter = new Intl.DateTimeFormat('es-AR', { weekday: 'short', day: '2-digit', month: '2-digit' })
const timeFormatter = new Intl.DateTimeFormat('es-AR', { hour: '2-digit', minute: '2-digit' })

function formatDay(value: string) {
  const [year, month, day] = value.slice(0, 10).split('-').map(Number)
  return dayFormatter.format(new Date(year, month - 1, day))
}

function formatTime(value: string) {
  return timeFormatter.format(new Date(/[zZ]|[+-]\d{2}:?\d{2}$/.test(value) ? value : `${value}Z`))
}

function vibrate(pattern: number | number[]) {
  try {
    navigator.vibrate?.(pattern)
  } catch {
    // Sin vibración disponible.
  }
}

export function UnloadControlPage() {
  const [params, setParams] = useSearchParams()
  const controlId = params.get('control')
  const type: ControlType = params.get('modo') === 'carga' ? 'CARGA' : 'DESCARGA'
  const { branch } = useActiveBranch()

  function openControl(id: string | null) {
    const next = new URLSearchParams()
    if (type === 'CARGA') next.set('modo', 'carga')
    if (id) next.set('control', id)
    setParams(next, { replace: false })
  }

  function setType(value: ControlType) {
    setParams(value === 'CARGA' ? { modo: 'carga' } : {}, { replace: true })
  }

  return (
    <main className="unload-page">
      <PageHeader
        icon={ClipboardCheck}
        title="Carga y descarga"
        description="Escaneá cada paquete en cada traspaso: al cargar el vehículo antes de salir y al descargarlo cuando llega. El sistema lo compara con lo que tenía que viajar y avisa lo que falta o sobra."
        actions={
          controlId ? (
            <button className="btn" type="button" onClick={() => openControl(null)}>
              <ArrowLeft size={17} aria-hidden="true" />
              Recorridos
            </button>
          ) : undefined
        }
      />

      {controlId ? (
        <ControlView key={controlId} controlId={controlId} />
      ) : (
        <>
          <div className="segmented unload-mode" role="group" aria-label="Qué vas a controlar">
            <button type="button" aria-pressed={type === 'DESCARGA'} onClick={() => setType('DESCARGA')}>
              <PackageCheck size={15} aria-hidden="true" />
              Descarga · lo que llega
            </button>
            <button type="button" aria-pressed={type === 'CARGA'} onClick={() => setType('CARGA')}>
              <Truck size={15} aria-hidden="true" />
              Carga · lo que sale
            </button>
          </div>
          <ActiveBranchNote action={type === 'CARGA' ? 'Recorridos que salen de' : 'Recorridos que llegan a'} />
          {branch ? (
            <IncomingRoutes key={`${type}-${branch.id}`} type={type} branchId={branch.id} branchName={branch.name} onOpen={openControl} />
          ) : null}
        </>
      )}
    </main>
  )
}

function IncomingRoutes({ type, branchId, branchName, onOpen }: { type: ControlType; branchId: number; branchName?: string; onOpen: (id: string) => void }) {
  const routes = useRoutesToControl(branchId, type)
  const loading = type === 'CARGA'
  const { start } = useUnloadMutations()

  function begin(route: IncomingRoute) {
    if (route.controlId) {
      onOpen(route.controlId)
      return
    }
    start.mutate(
      { routeId: route.routeId, branchId, type },
      {
        onSuccess: (control) => onOpen(control.id),
        onError: (error) => showToast(error.message, 'error'),
      },
    )
  }

  return (
    <section className="list-card" aria-labelledby="unload-routes-title">
      <div className="list-toolbar">
        <h2 className="list-toolbar__title" id="unload-routes-title">
          {loading ? `Recorridos que salen${branchName ? ` de ${branchName}` : ''}` : `Recorridos que llegan${branchName ? ` a ${branchName}` : ''}`}
          <small>{loading ? 'Generados, todavía sin salir' : 'Últimos 7 días'}</small>
        </h2>
        <button className="btn btn--ghost" type="button" onClick={() => void routes.refetch()} disabled={routes.isFetching}>
          <RefreshCw size={16} className={routes.isFetching ? 'loading-icon' : undefined} aria-hidden="true" />
          Actualizar
        </button>
      </div>

      {routes.isPending ? (
        <p className="unload-loading" role="status">
          <LoaderCircle className="loading-icon" size={18} aria-hidden="true" />
          Buscando recorridos…
        </p>
      ) : routes.isError ? (
        <div className="list-empty" role="alert">
          <CircleAlert size={28} aria-hidden="true" />
          <strong>No pudimos cargar los recorridos</strong>
          <p>{routes.error.message}</p>
        </div>
      ) : !routes.data.length ? (
        <div className="list-empty">
          <Truck size={30} aria-hidden="true" />
          <strong>{loading ? 'No hay recorridos para cargar' : 'No hay recorridos para descargar'}</strong>
          <p>{loading
            ? 'Acá aparecen los recorridos generados en esta sucursal que todavía no salieron.'
            : 'Acá aparecen los recorridos de larga distancia que ya salieron y dejan paquetes en esta sucursal.'}</p>
        </div>
      ) : (
        <ul className="list-rows">
          {routes.data.map((route) => {
            const closed = route.controlStatus === 'CERRADO'
            const complete = route.expected > 0 && route.verified === route.expected
            return (
              <li key={route.routeId} className={`list-row ${closed ? 'list-row--success' : route.controlStatus ? 'list-row--brand' : 'list-row--muted'}`}>
                <span className="unload-route__icon" aria-hidden="true">
                  <Truck size={18} />
                </span>
                <div className="list-row__main">
                  <p className="list-row__title">
                    {loading ? `${route.distanceType === 'CORTA' ? 'Reparto a domicilio' : 'Viaje entre sucursales'}` : `Desde ${route.originBranch}`}
                    <span className={`badge ${route.status === 'EN_CURSO' ? '' : 'badge--muted'}`}>
                      {route.status === 'EN_CURSO' ? 'En viaje' : route.status === 'FINALIZADO' ? 'Recorrido finalizado' : 'Sin salir'}
                    </span>
                    <span className={`badge ${closed ? 'badge--success' : route.controlStatus ? 'badge--info' : 'badge--warning'}`}>
                      {closed ? 'Control cerrado' : route.controlStatus ? 'Control en curso' : 'Sin controlar'}
                    </span>
                  </p>
                  <p className="list-row__meta">
                    <span>{route.driverName}</span>
                    <span>{formatDay(route.date)}</span>
                    <span>{route.expected} {route.expected === 1 ? 'paquete' : 'paquetes'} {loading ? 'para cargar' : 'para esta sucursal'}</span>
                  </p>
                  <div className="unload-progress" aria-label={`${route.verified} de ${route.expected} verificados`}>
                    <span style={{ width: `${route.expected ? (route.verified / route.expected) * 100 : 0}%` }} className={complete ? 'is-complete' : ''} />
                  </div>
                </div>
                <div className="list-row__aside">
                  <button
                    className={`btn ${closed ? '' : 'btn--primary'}`}
                    type="button"
                    disabled={start.isPending}
                    onClick={() => begin(route)}
                  >
                    {start.isPending && start.variables?.routeId === route.routeId ? (
                      <LoaderCircle className="loading-icon" size={16} aria-hidden="true" />
                    ) : closed ? (
                      <PackageSearch size={16} aria-hidden="true" />
                    ) : (
                      <ScanBarcode size={16} aria-hidden="true" />
                    )}
                    {closed ? 'Ver resumen' : route.controlStatus ? 'Continuar' : loading ? 'Empezar carga' : 'Empezar descarga'}
                  </button>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}

type ListTab = 'faltan' | 'verificados' | 'sobrantes'

function ControlView({ controlId }: { controlId: string }) {
  const controlQuery = useUnloadControl(controlId)
  const { read, close } = useUnloadMutations()
  const [code, setCode] = useState('')
  const [last, setLast] = useState<ReadOutcome | null>(null)
  const [tab, setTab] = useState<ListTab>('faltan')
  const [closing, setClosing] = useState(false)
  const [notes, setNotes] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const control = controlQuery.data

  function submit(value: string) {
    const normalized = value.replace(/\s+/g, '').toUpperCase()
    if (!normalized || read.isPending) return
    read.mutate(
      { controlId, code: normalized },
      {
        onSuccess: (outcome) => {
          setLast(outcome)
          setCode('')
          vibrate(outcome.result === 'CORRECTO' && !outcome.repeated ? 60 : [120, 60, 120])
          inputRef.current?.focus()
        },
        onError: (error) => {
          setLast(null)
          showToast(error.message, 'error')
          inputRef.current?.focus()
        },
      },
    )
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    submit(code)
  }

  if (controlQuery.isPending) {
    return (
      <p className="unload-loading" role="status">
        <LoaderCircle className="loading-icon" size={18} aria-hidden="true" />
        Abriendo el control…
      </p>
    )
  }

  if (controlQuery.isError || !control) {
    return (
      <div className="list-card list-empty" role="alert">
        <CircleAlert size={28} aria-hidden="true" />
        <strong>No pudimos abrir el control</strong>
        <p>{controlQuery.error?.message}</p>
      </div>
    )
  }

  const open = control.status === 'EN_CURSO'
  const loading = control.type === 'CARGA'
  const pending = control.expected.filter((item) => !item.verified)
  const verified = control.expected.filter((item) => item.verified)
  const percent = control.totalExpected ? Math.round((control.verified / control.totalExpected) * 100) : 0

  return (
    <>
      <section className="surface-card unload-hero" aria-labelledby="unload-hero-title">
        <div className="unload-hero__route">
          <p className="eyebrow">{loading ? 'Control de carga' : 'Control de descarga'}</p>
          <h2 id="unload-hero-title">
            {loading ? `Sale de ${control.branch.name}` : `${control.route.originBranch} → ${control.branch.name}`}
          </h2>
          <p>
            {control.route.driverName} · {formatDay(control.route.date)} · iniciado por {control.startedBy ?? '—'} a las {formatTime(control.createdAt)}
          </p>
          <div className="unload-chips">
            <span className="unload-chip tone-success"><PackageCheck size={15} aria-hidden="true" />{control.verified} {control.verified === 1 ? 'verificado' : 'verificados'}</span>
            <span className={`unload-chip ${control.missing ? 'tone-danger' : 'tone-neutral'}`}><Clock3 size={15} aria-hidden="true" />{control.missing} {open ? 'por llegar' : control.missing === 1 ? 'faltante' : 'faltantes'}</span>
            <span className={`unload-chip ${control.extras.length ? 'tone-warning' : 'tone-neutral'}`}><PackageX size={15} aria-hidden="true" />{control.extras.length} {control.extras.length === 1 ? 'sobrante' : 'sobrantes'}</span>
          </div>
        </div>
        <div className="unload-ring" style={{ '--progress': `${percent * 3.6}deg` } as CSSProperties} role="img" aria-label={`${control.verified} de ${control.totalExpected} paquetes verificados`}>
          <div>
            <strong>{control.verified}</strong>
            <span>de {control.totalExpected}</span>
          </div>
        </div>
      </section>

      {open ? (
        <section className="surface-card unload-scan" aria-labelledby="unload-scan-title">
          <h2 id="unload-scan-title">
            <ScanBarcode size={18} aria-hidden="true" />
            {loading ? 'Escaneá cada paquete que sube al vehículo' : 'Escaneá cada paquete que baja'}
          </h2>
          <form className="unload-scan__form" onSubmit={handleSubmit}>
            <label className="visually-hidden" htmlFor="unload-code">Código del paquete</label>
            <input
              ref={inputRef}
              id="unload-code"
              className="form-control unload-scan__input"
              placeholder="PAQ-XXXXXXXXXX"
              value={code}
              onChange={(event) => setCode(event.target.value)}
              autoComplete="off"
              spellCheck={false}
              autoFocus
            />
            <button className="btn btn--primary" type="submit" disabled={!code.trim() || read.isPending}>
              {read.isPending ? <LoaderCircle className="loading-icon" size={17} aria-hidden="true" /> : <PackageCheck size={17} aria-hidden="true" />}
              Registrar
            </button>
            <ScanWithCameraButton
              mode="continuous"
              className="btn"
              pattern={PACKAGE_CODE_PATTERN}
              patternMessage={(value) => `${value} no es un código de paquete (PAQ-XXXXXXXXXX).`}
              onScan={(value) => {
                if (read.isPending) return 'Esperá a que termine la lectura anterior.'
                submit(value)
              }}
              description={loading ? 'Apuntá la cámara a la etiqueta de cada paquete que suben al vehículo.' : 'Apuntá la cámara a la etiqueta de cada paquete que bajan. Cada lectura se registra sola.'}
              continuousHint="El resultado de cada paquete aparece en la pantalla del control."
            />
          </form>
          <p className="unload-scan__hint">Con lector USB, cada lectura se registra sola. Si un código se lee dos veces, no se cuenta de nuevo.</p>

          {last ? (
            <div
              className={`unload-result ${last.repeated ? 'tone-neutral' : last.result === 'CORRECTO' ? 'tone-success' : last.result === 'SOBRANTE' ? 'tone-warning' : 'tone-danger'}`}
              role="status"
              aria-live="assertive"
            >
              {last.result === 'CORRECTO' && !last.repeated ? <CheckCircle2 size={26} aria-hidden="true" /> : <CircleAlert size={26} aria-hidden="true" />}
              <div>
                <strong>{last.code}</strong>
                <p>{last.message}</p>
                {last.readyForPickup && <p className="unload-result__hint">Se avisó al destinatario que ya puede retirarlo.</p>}
              </div>
            </div>
          ) : null}
        </section>
      ) : (
        <section className="surface-card unload-closed" role="status">
          <Lock size={22} aria-hidden="true" />
          <div>
            <strong>Control cerrado</strong>
            <p>
              {control.summary} Cerrado por {control.closedBy ?? '—'}
              {control.closedAt ? ` a las ${formatTime(control.closedAt)}` : ''}.
            </p>
            {control.notes ? <p>Observaciones: {control.notes}</p> : null}
            {control.missing ? (
              <Link className="monitor-link" to="/monitor/incidencias?grupo=FALTANTES">
                Ver los faltantes en el monitor
              </Link>
            ) : null}
          </div>
        </section>
      )}

      <FilterTabs<ListTab>
        label="Paquetes del control"
        value={tab}
        onChange={setTab}
        tabs={[
          { id: 'faltan', label: open ? (loading ? 'Por cargar' : 'Por llegar') : 'Faltantes', count: pending.length, icon: Clock3 },
          { id: 'verificados', label: 'Verificados', count: verified.length, icon: PackageCheck },
          { id: 'sobrantes', label: 'Sobrantes', count: control.extras.length, icon: PackageX },
        ]}
      />

      <section className="list-card">
        {tab === 'sobrantes' ? (
          control.extras.length ? (
            <ul className="list-rows">
              {control.extras.map((item) => (
                <li className={`list-row ${item.result === 'SOBRANTE' ? 'list-row--brand' : 'list-row--muted'}`} key={item.code}>
                  <span className="unload-route__icon tone-warning" aria-hidden="true"><PackageX size={18} /></span>
                  <div className="list-row__main">
                    <p className="list-row__title">
                      <span className="unload-code">{item.code}</span>
                      <span className={`badge ${item.result === 'SOBRANTE' ? 'badge--warning' : 'badge--danger'}`}>
                        {item.result === 'SOBRANTE' ? 'No corresponde' : 'Código desconocido'}
                      </span>
                    </p>
                    <p className="list-row__meta"><span>{item.detail}</span></p>
                    <p className="list-row__meta"><span>Leído por {item.userName ?? '—'} a las {formatTime(item.createdAt)}</span></p>
                  </div>
                  {item.result === 'SOBRANTE' ? (
                    <div className="list-row__aside">
                      <Link className="icon-action" to={`/monitor/trazabilidad/${item.code}`} title="Ver trazabilidad" aria-label={`Ver la trazabilidad de ${item.code}`}>
                        <PackageSearch size={17} aria-hidden="true" />
                      </Link>
                    </div>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <div className="list-empty"><CheckCircle2 size={28} aria-hidden="true" /><strong>Sin sobrantes</strong><p>Todo lo leído corresponde a esta descarga.</p></div>
          )
        ) : (
          (tab === 'faltan' ? pending : verified).length ? (
            <ul className="list-rows">
              {(tab === 'faltan' ? pending : verified).map((item) => (
                <li className={`list-row ${item.verified ? 'list-row--success' : open ? 'list-row--muted' : 'list-row--brand'}`} key={item.id}>
                  <span className={`unload-route__icon ${item.verified ? 'tone-success' : open ? 'tone-neutral' : 'tone-danger'}`} aria-hidden="true">
                    {item.verified ? <PackageCheck size={18} /> : <Clock3 size={18} />}
                  </span>
                  <div className="list-row__main">
                    <p className="list-row__title">
                      <span className="unload-code">{item.code}</span>
                      {!loading && <span className="badge badge--muted">{item.deliveryType === 'domicilio' ? 'Sigue a domicilio' : 'Queda para retiro'}</span>}
                    </p>
                    <p className="list-row__meta">
                      <span>{item.description}</span>
                      <span>Para {item.recipientName}</span>
                      {item.verified ? <span>Verificado por {item.verifiedBy ?? '—'} a las {item.verifiedAt ? formatTime(item.verifiedAt) : '—'}</span> : null}
                    </p>
                  </div>
                  <div className="list-row__aside">
                    <Link className="icon-action" to={`/monitor/trazabilidad/${item.code}`} title="Ver trazabilidad" aria-label={`Ver la trazabilidad de ${item.code}`}>
                      <PackageSearch size={17} aria-hidden="true" />
                    </Link>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <div className="list-empty">
              <CheckCircle2 size={28} aria-hidden="true" />
              <strong>{tab === 'faltan' ? (loading ? 'Se cargó todo lo previsto' : 'Llegó todo lo esperado') : 'Todavía no se verificó ningún paquete'}</strong>
              <p>{tab === 'faltan' ? 'Podés cerrar el control.' : 'Escaneá el primer paquete que baja.'}</p>
            </div>
          )
        )}
      </section>

      {open ? (
        <div className="unload-footer">
          <button className="btn btn--primary" type="button" onClick={() => setClosing(true)}>
            <Lock size={17} aria-hidden="true" />
            {loading ? 'Terminar carga y cerrar control' : 'Terminar descarga y cerrar control'}
          </button>
        </div>
      ) : null}

      <CloseModal
        open={closing}
        control={control}
        notes={notes}
        pending={close.isPending}
        error={close.error?.message ?? null}
        onNotes={setNotes}
        onCancel={() => setClosing(false)}
        onConfirm={() =>
          close.mutate(
            { controlId, notes },
            {
              onSuccess: ({ message }) => {
                setClosing(false)
                showToast(message ?? 'Control cerrado.', control.missing ? 'error' : 'success')
              },
            },
          )
        }
      />
    </>
  )
}

interface CloseModalProps {
  open: boolean
  control: UnloadControl
  notes: string
  pending: boolean
  error: string | null
  onNotes: (value: string) => void
  onCancel: () => void
  onConfirm: () => void
}

function CloseModal({ open, control, notes, pending, error, onNotes, onCancel, onConfirm }: CloseModalProps) {
  const missing = control.expected.filter((item) => !item.verified)
  return (
    <Modal
      open={open}
      onClose={onCancel}
      icon={Lock}
      eyebrow="Cerrar control"
      title={missing.length ? `${missing.length === 1 ? 'Falta 1 paquete' : `Faltan ${missing.length} paquetes`}` : 'Llegó todo lo esperado'}
      description={
        missing.length
          ? control.type === 'CARGA'
            ? 'Al cerrar, lo que no se cargó sale del recorrido y queda en la sucursal para el próximo. Después no se pueden registrar más lecturas.'
            : 'Al cerrar, cada faltante queda como incidencia en el monitor para que se investigue. Después no se pueden registrar más lecturas.'
          : 'Se verificaron todos los paquetes. Después de cerrar no se pueden registrar más lecturas.'
      }
      footer={
        <>
          <button className="btn btn--ghost" type="button" onClick={onCancel}>Seguir escaneando</button>
          <button className="btn btn--primary" type="button" disabled={pending} onClick={onConfirm}>
            {pending ? <LoaderCircle className="loading-icon" size={17} aria-hidden="true" /> : <Lock size={17} aria-hidden="true" />}
            Cerrar control
          </button>
        </>
      }
    >
      <p className="unload-close__summary">{control.summary}</p>
      {missing.length ? (
        <ul className="unload-close__list">
          {missing.slice(0, 8).map((item) => (
            <li key={item.id}><span className="unload-code">{item.code}</span> · {item.description}</li>
          ))}
          {missing.length > 8 ? <li>y {missing.length - 8} más…</li> : null}
        </ul>
      ) : null}
      <div className="form-field">
        <label htmlFor="unload-notes">Observaciones (opcional)</label>
        <textarea
          id="unload-notes"
          className="form-control unload-close__notes"
          rows={3}
          maxLength={1000}
          placeholder="Ej.: el chofer avisa que una caja quedó en el depósito de origen."
          value={notes}
          onChange={(event) => onNotes(event.target.value)}
        />
      </div>
      {error ? (
        <p className="form-error" role="alert">
          <CircleAlert size={18} aria-hidden="true" />
          {error}
        </p>
      ) : null}
    </Modal>
  )
}
