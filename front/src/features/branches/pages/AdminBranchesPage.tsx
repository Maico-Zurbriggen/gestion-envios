import { useState } from 'react'
import { Building2, CircleOff, MapPin, MapPinOff, Pencil, Plus, RefreshCw, UsersRound } from 'lucide-react'
import { PageHeader } from '../../../shared/components/PageHeader'
import { showToast } from '../../../shared/services/toast'
import { BranchFormModal } from '../components/BranchFormModal'
import { useAdminBranches, useSaveBranch } from '../hooks/useAdminBranches'
import type { AdminBranch, BranchInput } from '../types/branch.types'
import './AdminBranchesPage.css'

/** Alta y edición de sucursales: su dirección es el punto de partida de los recorridos. */
export function AdminBranchesPage() {
  const branches = useAdminBranches()
  const save = useSaveBranch()
  const [editing, setEditing] = useState<AdminBranch | null>(null)
  const [creating, setCreating] = useState(false)

  function close() {
    setEditing(null)
    setCreating(false)
    save.reset()
  }

  function submit(input: BranchInput) {
    save.mutate({ id: editing?.id ?? null, input }, {
      onSuccess: ({ message }) => {
        showToast(message)
        close()
      },
    })
  }

  return (
    <main className="admin-branches">
      <PageHeader
        icon={Building2}
        eyebrow="Administración"
        title="Sucursales"
        description="Cada usuario trabaja solo en las sucursales que tiene habilitadas. La dirección de cada una es de donde parten sus recorridos."
        actions={
          <button className="btn btn--primary" type="button" onClick={() => setCreating(true)}>
            <Plus size={18} aria-hidden="true" /> Nueva sucursal
          </button>
        }
      />

      <section className="list-card" aria-labelledby="branches-list-title">
        <div className="list-toolbar">
          <h2 className="list-toolbar__title" id="branches-list-title">
            Sucursales
            <small>{branches.data ? `${branches.data.length} en total` : ''}</small>
          </h2>
        </div>
        {branches.isPending ? (
          <p className="list-empty" role="status">Cargando sucursales…</p>
        ) : branches.isError ? (
          <div className="list-empty" role="alert">
            <strong>No pudimos cargar las sucursales</strong>
            <p>{branches.error.message}</p>
            <button className="btn" type="button" onClick={() => void branches.refetch()}>
              <RefreshCw size={16} aria-hidden="true" /> Reintentar
            </button>
          </div>
        ) : (
          <ul className="list-rows">
            {branches.data.map((branch) => {
              const located = branch.latitude !== null && branch.longitude !== null
              return (
                <li className={`list-row ${branch.active ? 'list-row--success' : 'list-row--muted'}`} key={branch.id}>
                  <span className="list-row__avatar" aria-hidden="true"><Building2 size={18} /></span>
                  <div className="list-row__main">
                    <p className="list-row__title">
                      {branch.name}
                      {!branch.active && <span className="badge badge--danger"><CircleOff size={12} aria-hidden="true" /> Inactiva</span>}
                      {!located && <span className="badge badge--warning"><MapPinOff size={12} aria-hidden="true" /> Sin ubicar</span>}
                    </p>
                    <p className="list-row__meta">
                      <span><MapPin size={13} aria-hidden="true" /> {branch.address}, {branch.city}, {branch.province}</span>
                      <span><UsersRound size={13} aria-hidden="true" /> {branch.users} {branch.users === 1 ? 'usuario habilitado' : 'usuarios habilitados'}</span>
                    </p>
                  </div>
                  <div className="list-row__aside">
                    <button className="icon-action" type="button" title="Editar" aria-label={`Editar ${branch.name}`} onClick={() => setEditing(branch)}>
                      <Pencil size={17} aria-hidden="true" />
                    </button>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </section>

      <BranchFormModal
        open={creating || editing !== null}
        branch={editing}
        pending={save.isPending}
        error={save.error?.message ?? null}
        onClose={close}
        onSubmit={submit}
      />
    </main>
  )
}
