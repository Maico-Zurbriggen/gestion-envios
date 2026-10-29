import { useDeferredValue, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Building2,
  Bike,
  KeyRound,
  LoaderCircle,
  Pencil,
  RefreshCw,
  Search,
  ShieldCheck,
  UserCheck,
  UserPlus,
  UserRoundX,
  UsersRound,
  UserX,
} from 'lucide-react'
import { useAppSelector } from '../../../app/store'
import { FilterTabs, PageHeader, StatCard } from '../../../shared/components/PageHeader'
import { Modal } from '../../../shared/components/Modal'
import { showToast } from '../../../shared/services/toast'
import { selectCurrentUser } from '../../auth/redux/authSlice'
import { useAdminBranches } from '../../branches/hooks/useAdminBranches'
import { TemporaryPasswordModal } from '../components/TemporaryPasswordModal'
import { UserFormModal } from '../components/UserFormModal'
import { useEmployeeMutations, useEmployees } from '../hooks/useEmployees'
import { useRoles } from '../hooks/useRoles'
import type { CreateUserInput, Employee, EmployeeStatus } from '../types/user.types'
import { initials, roleLabel } from '../../../shared/utils/roles'
import './UsersPage.css'

type StatusTab = 'all' | EmployeeStatus

type Confirmation = { kind: 'status' | 'password'; employee: Employee } | null

const dateFormatter = new Intl.DateTimeFormat('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' })

function formatDate(value: string | null) {
  return value ? dateFormatter.format(new Date(value)) : null
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : null
}

export function UsersPage() {
  const currentUser = useAppSelector(selectCurrentUser)
  const [searchParams, setSearchParams] = useSearchParams()
  const [statusTab, setStatusTab] = useState<StatusTab>('all')
  const [roleId, setRoleId] = useState<number | null>(null)
  const [search, setSearch] = useState('')
  const deferredSearch = useDeferredValue(search)
  const [editing, setEditing] = useState<Employee | null>(null)
  const [creating, setCreating] = useState(() => searchParams.get('nuevo') === '1')
  const [confirmation, setConfirmation] = useState<Confirmation>(null)
  const [password, setPassword] = useState<{ name: string; password: string; created: boolean } | null>(null)

  const rolesQuery = useRoles()
  const branchOptions = useAdminBranches().data ?? []
  const roles = rolesQuery.data ?? []
  const employeesQuery = useEmployees({
    search: deferredSearch,
    roleId,
    status: statusTab === 'all' ? null : statusTab,
  })
  const { create, update, changeStatus, resetPassword } = useEmployeeMutations()

  const summary = employeesQuery.data?.summary
  const employees = employeesQuery.data?.employees ?? []
  const filtersActive = Boolean(deferredSearch.trim() || roleId || statusTab !== 'all')

  function openCreate() {
    create.reset()
    setCreating(true)
  }

  function closeCreate() {
    setCreating(false)
    if (searchParams.has('nuevo')) setSearchParams({}, { replace: true })
  }

  function openEdit(employee: Employee) {
    update.reset()
    setEditing(employee)
  }

  function submitCreate(input: CreateUserInput) {
    create.mutate(input, {
      onSuccess: (user) => {
        closeCreate()
        setPassword({ name: user.name, password: user.temporaryPassword, created: true })
        showToast(`${user.name} quedó registrado como ${roleLabel(user.role).toLowerCase()}.`)
      },
    })
  }

  function submitEdit(input: CreateUserInput) {
    if (!editing) return
    // Se envían solo los campos que cambiaron.
    const changes: Partial<CreateUserInput> = {}
    if (input.name !== editing.name) changes.name = input.name
    if (input.dni !== editing.dni) changes.dni = input.dni
    if (input.email.toLowerCase() !== editing.email) changes.email = input.email
    if (input.phone !== editing.phone) changes.phone = input.phone
    if (input.roleId !== editing.roleId) changes.roleId = input.roleId
    const before = editing.branches.map((branch) => branch.id).sort().join(',')
    if ([...input.branchIds].sort().join(',') !== before) changes.branchIds = input.branchIds
    if (!Object.keys(changes).length) {
      setEditing(null)
      return
    }
    update.mutate(
      { id: editing.id, input: changes },
      {
        onSuccess: (employee) => {
          setEditing(null)
          showToast(`Se guardaron los cambios de ${employee.name}.`)
        },
      },
    )
  }

  function confirmAction() {
    if (!confirmation) return
    const { employee, kind } = confirmation
    if (kind === 'status') {
      changeStatus.mutate(
        { id: employee.id, status: employee.status === 'Activo' ? 'Inactivo' : 'Activo' },
        {
          onSuccess: ({ message }) => {
            setConfirmation(null)
            showToast(message)
          },
          onError: (error) => showToast(errorMessage(error) ?? 'No pudimos cambiar el estado.', 'error'),
        },
      )
    } else {
      resetPassword.mutate(employee.id, {
        onSuccess: (result) => {
          setConfirmation(null)
          setPassword({ name: result.name, password: result.temporaryPassword, created: false })
        },
        onError: (error) => showToast(errorMessage(error) ?? 'No pudimos blanquear la contraseña.', 'error'),
      })
    }
  }

  const confirmPending = changeStatus.isPending || resetPassword.isPending
  const deactivating = confirmation?.kind === 'status' && confirmation.employee.status === 'Activo'

  return (
    <main className="users-page">
      <PageHeader
        icon={UsersRound}
        eyebrow="Administración"
        title="Usuarios"
        description="Registrá al personal, asigná roles, blanqueá contraseñas y controlá quién puede ingresar al sistema."
        actions={
          <button className="btn btn--primary" type="button" onClick={openCreate}>
            <UserPlus size={18} aria-hidden="true" />
            Nuevo usuario
          </button>
        }
      />

      <section className="stat-grid" aria-label="Resumen del personal">
        <StatCard label="Usuarios" value={summary?.total ?? '—'} icon={UsersRound} hint="Personal registrado" />
        <StatCard label="Activos" value={summary?.active ?? '—'} icon={UserCheck} tone="success" hint="Pueden ingresar" />
        <StatCard label="Dados de baja" value={summary?.inactive ?? '—'} icon={UserRoundX} tone="muted" hint="Sin acceso" />
        <StatCard
          label="Repartidores"
          value={summary ? (summary.byRole.REPARTIDOR ?? 0) : '—'}
          icon={Bike}
          tone="info"
          hint="Disponibles para recorridos"
        />
      </section>

      <FilterTabs<StatusTab>
        label="Filtrar por estado"
        value={statusTab}
        onChange={setStatusTab}
        tabs={[
          { id: 'all', label: 'Todos', count: summary?.total },
          { id: 'Activo', label: 'Activos', count: summary?.active, icon: UserCheck },
          { id: 'Inactivo', label: 'Dados de baja', count: summary?.inactive, icon: UserX },
        ]}
      />

      <section className="list-card" aria-labelledby="users-list-title">
        <div className="list-toolbar">
          <h2 className="list-toolbar__title" id="users-list-title">
            Personal
            <small>
              {employeesQuery.data ? `${employeesQuery.data.total} ${employeesQuery.data.total === 1 ? 'usuario' : 'usuarios'}` : ''}
            </small>
          </h2>
          <div className="list-toolbar__controls">
            <label className="visually-hidden" htmlFor="users-role-filter">
              Filtrar por rol
            </label>
            <select
              className="list-select"
              id="users-role-filter"
              value={roleId ?? ''}
              onChange={(event) => setRoleId(event.target.value ? Number(event.target.value) : null)}
            >
              <option value="">Todos los roles</option>
              {roles.map((role) => (
                <option key={role.id} value={role.id}>
                  {roleLabel(role.name)}
                  {summary?.byRole[role.name] !== undefined ? ` (${summary.byRole[role.name]})` : ''}
                </option>
              ))}
            </select>
            <div className="list-search">
              <Search size={16} aria-hidden="true" />
              <label className="visually-hidden" htmlFor="users-search">
                Buscar usuarios
              </label>
              <input
                id="users-search"
                type="search"
                placeholder="Buscar por nombre, DNI, email o teléfono"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>
          </div>
        </div>

        {employeesQuery.isPending ? (
          <ul className="list-rows" aria-busy="true" aria-label="Cargando usuarios">
            {[0, 1, 2, 3].map((item) => (
              <li className="list-row" key={item}>
                <span className="skeleton users-skeleton__avatar" />
                <span className="users-skeleton__lines">
                  <span className="skeleton" />
                  <span className="skeleton" />
                </span>
              </li>
            ))}
          </ul>
        ) : employeesQuery.isError ? (
          <div className="list-empty" role="alert">
            <UserRoundX size={30} aria-hidden="true" />
            <strong>No pudimos cargar los usuarios</strong>
            <p>{errorMessage(employeesQuery.error)}</p>
            <button className="btn" type="button" onClick={() => void employeesQuery.refetch()}>
              <RefreshCw size={16} aria-hidden="true" />
              Reintentar
            </button>
          </div>
        ) : employees.length === 0 ? (
          <div className="list-empty">
            <Search size={30} aria-hidden="true" />
            <strong>{filtersActive ? 'Ningún usuario coincide con el filtro' : 'Todavía no hay usuarios'}</strong>
            <p>
              {filtersActive
                ? 'Probá con otra búsqueda o quitá los filtros de rol y estado.'
                : 'Registrá al primer integrante del personal con el botón Nuevo usuario.'}
            </p>
          </div>
        ) : (
          <ul className={`list-rows ${employeesQuery.isFetching ? 'is-refreshing' : ''}`}>
            {employees.map((employee) => {
              const isSelf = employee.id === currentUser?.id
              const active = employee.status === 'Activo'
              const since = formatDate(employee.createdAt)
              return (
                <li className={`list-row ${active ? 'list-row--success' : 'list-row--muted'}`} key={employee.id}>
                  <span className="list-row__avatar" aria-hidden="true">
                    {initials(employee.name)}
                  </span>
                  <div className="list-row__main">
                    <p className="list-row__title">
                      {employee.name}
                      {isSelf ? <span className="badge badge--info">Vos</span> : null}
                      <span className={`badge ${employee.role === 'SUPERADMIN' ? '' : 'badge--muted'}`}>
                        {employee.role === 'SUPERADMIN' ? <ShieldCheck size={12} aria-hidden="true" /> : null}
                        {roleLabel(employee.role)}
                      </span>
                      <span className={`badge ${active ? 'badge--success' : 'badge--danger'}`}>
                        {active ? 'Activo' : 'Dado de baja'}
                      </span>
                      {employee.requiresPasswordChange ? (
                        <span className="badge badge--warning">Contraseña temporal</span>
                      ) : null}
                    </p>
                    <p className="list-row__meta">
                      <span>DNI {employee.dni}</span>
                      <span>{employee.email}</span>
                      <span>{employee.phone}</span>
                      {since ? <span>Alta {since}</span> : null}
                    </p>
                    {employee.branches.length ? (
                      <p className="list-row__meta user-row__branches">
                        <Building2 size={13} aria-hidden="true" />
                        <span>{employee.branches.map((branch) => branch.name).join(' · ')}</span>
                      </p>
                    ) : null}
                  </div>
                  <div className="list-row__aside">
                    <button
                      className="icon-action"
                      type="button"
                      title="Editar datos y rol"
                      aria-label={`Editar a ${employee.name}`}
                      onClick={() => openEdit(employee)}
                    >
                      <Pencil size={17} aria-hidden="true" />
                    </button>
                    <button
                      className="icon-action"
                      type="button"
                      title={isSelf ? 'Usá Cambiar contraseña desde tu sesión' : 'Blanquear contraseña'}
                      aria-label={`Blanquear la contraseña de ${employee.name}`}
                      disabled={isSelf || !active}
                      onClick={() => setConfirmation({ kind: 'password', employee })}
                    >
                      <KeyRound size={17} aria-hidden="true" />
                    </button>
                    <button
                      className={`icon-action ${active ? 'icon-action--danger' : 'icon-action--success'}`}
                      type="button"
                      title={isSelf ? 'No podés dar de baja tu propio usuario' : active ? 'Dar de baja' : 'Reactivar'}
                      aria-label={`${active ? 'Dar de baja' : 'Reactivar'} a ${employee.name}`}
                      disabled={isSelf}
                      onClick={() => setConfirmation({ kind: 'status', employee })}
                    >
                      {active ? <UserX size={17} aria-hidden="true" /> : <UserCheck size={17} aria-hidden="true" />}
                    </button>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </section>

      <UserFormModal
        open={creating}
        roles={roles}
        rolesLoading={rolesQuery.isPending}
        branches={branchOptions}
        isSelf={false}
        pending={create.isPending}
        error={errorMessage(create.error)}
        onClose={closeCreate}
        onSubmit={submitCreate}
      />

      <UserFormModal
        open={Boolean(editing)}
        employee={editing}
        roles={roles}
        rolesLoading={rolesQuery.isPending}
        branches={branchOptions}
        isSelf={editing?.id === currentUser?.id}
        pending={update.isPending}
        error={errorMessage(update.error)}
        onClose={() => setEditing(null)}
        onSubmit={submitEdit}
      />

      <Modal
        open={Boolean(confirmation)}
        onClose={() => setConfirmation(null)}
        size="narrow"
        icon={confirmation?.kind === 'password' ? KeyRound : deactivating ? UserX : UserCheck}
        eyebrow="Confirmar acción"
        title={
          confirmation?.kind === 'password'
            ? 'Blanquear contraseña'
            : deactivating
              ? 'Dar de baja al usuario'
              : 'Reactivar al usuario'
        }
        description={
          confirmation
            ? confirmation.kind === 'password'
              ? `Se genera una contraseña temporal nueva para ${confirmation.employee.name}. La actual deja de funcionar.`
              : deactivating
                ? `${confirmation.employee.name} no va a poder ingresar al sistema. Su historial se conserva y podés reactivarlo cuando quieras.`
                : `${confirmation.employee.name} va a poder volver a ingresar con su contraseña actual.`
            : undefined
        }
        footer={
          <>
            <button className="btn btn--ghost" type="button" onClick={() => setConfirmation(null)}>
              Cancelar
            </button>
            <button
              className={`btn ${deactivating ? 'btn--danger' : 'btn--primary'}`}
              type="button"
              disabled={confirmPending}
              onClick={confirmAction}
            >
              {confirmPending ? <LoaderCircle className="loading-icon" size={18} aria-hidden="true" /> : null}
              {confirmation?.kind === 'password' ? 'Blanquear' : deactivating ? 'Dar de baja' : 'Reactivar'}
            </button>
          </>
        }
      >
        {confirmation ? (
          <dl className="users-confirm">
            <div>
              <dt>Rol</dt>
              <dd>{roleLabel(confirmation.employee.role)}</dd>
            </div>
            <div>
              <dt>Email</dt>
              <dd>{confirmation.employee.email}</dd>
            </div>
          </dl>
        ) : null}
      </Modal>

      <TemporaryPasswordModal result={password} onClose={() => setPassword(null)} />
    </main>
  )
}
