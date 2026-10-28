import { useState, type FormEvent } from 'react'
import { IdCard, Info, LoaderCircle, Mail, Phone, Save, Shield, UserPen, UserPlus, UserRound } from 'lucide-react'
import { Modal } from '../../../shared/components/Modal'
import type { CreateUserInput, Employee, Role } from '../types/user.types'
import { roleLabel } from '../../../shared/utils/roles'

interface UserFormModalProps {
  open: boolean
  /** Usuario a editar; sin él, el formulario da de alta uno nuevo. */
  employee?: Employee | null
  roles: Role[]
  rolesLoading: boolean
  isSelf: boolean
  pending: boolean
  error: string | null
  onClose: () => void
  onSubmit: (input: CreateUserInput) => void
}

interface FormState {
  name: string
  dni: string
  email: string
  phone: string
  roleId: number | ''
}

function initialState(employee?: Employee | null): FormState {
  return employee
    ? { name: employee.name, dni: employee.dni, email: employee.email, phone: employee.phone, roleId: employee.roleId }
    : { name: '', dni: '', email: '', phone: '', roleId: '' }
}

export function UserFormModal(props: UserFormModalProps) {
  // El formulario se vuelve a montar cada vez que se abre, con los datos del usuario elegido.
  return (
    <Modal
      open={props.open}
      onClose={props.onClose}
      icon={props.employee ? UserPen : UserPlus}
      eyebrow={props.employee ? 'Editar usuario' : 'Nuevo usuario'}
      title={props.employee ? props.employee.name : 'Registrar usuario'}
      description={
        props.employee
          ? 'Actualizá los datos de contacto o el rol. Los cambios rigen desde su próxima acción.'
          : 'El sistema genera una contraseña temporal que el usuario cambia en su primer ingreso.'
      }
    >
      <UserForm key={props.employee?.id ?? 'nuevo'} {...props} />
    </Modal>
  )
}

function UserForm({ employee, roles, rolesLoading, isSelf, pending, error, onClose, onSubmit }: UserFormModalProps) {
  const [form, setForm] = useState<FormState>(() => initialState(employee))
  // En el alta no se ofrece Superadministrador (HU01); al editar sí, para poder delegar.
  const options = employee ? roles : roles.filter((role) => role.name !== 'SUPERADMIN')
  const selectedRole = roles.find((role) => role.id === form.roleId)

  function update<Key extends keyof FormState>(field: Key, value: FormState[Key]) {
    setForm((current) => ({ ...current, [field]: value }))
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (form.roleId === '') return
    onSubmit({
      name: form.name.trim(),
      dni: form.dni.trim(),
      email: form.email.trim(),
      phone: form.phone.trim(),
      roleId: form.roleId,
    })
  }

  const prefix = employee ? 'edit-user' : 'new-user'

  return (
    <form className="user-modal-form" onSubmit={handleSubmit}>
      <div className="user-modal-form__grid">
        <div className="form-field user-modal-form__full">
          <label htmlFor={`${prefix}-name`}>Nombre y apellido</label>
          <div className="input-control">
            <UserRound className="input-control__icon" size={18} aria-hidden="true" />
            <input
              className="form-control form-control--with-icon"
              id={`${prefix}-name`}
              autoComplete="off"
              placeholder="Ej. Carlos Gómez"
              value={form.name}
              onChange={(event) => update('name', event.target.value)}
              minLength={2}
              maxLength={100}
              required
              autoFocus
            />
          </div>
        </div>

        <div className="form-field">
          <label htmlFor={`${prefix}-dni`}>DNI</label>
          <div className="input-control">
            <IdCard className="input-control__icon" size={18} aria-hidden="true" />
            <input
              className="form-control form-control--with-icon"
              id={`${prefix}-dni`}
              inputMode="numeric"
              placeholder="35123456"
              value={form.dni}
              onChange={(event) => update('dni', event.target.value.replace(/\D/g, ''))}
              minLength={6}
              maxLength={20}
              pattern="[0-9]{6,20}"
              required
            />
          </div>
        </div>

        <div className="form-field">
          <label htmlFor={`${prefix}-phone`}>Teléfono</label>
          <div className="input-control">
            <Phone className="input-control__icon" size={18} aria-hidden="true" />
            <input
              className="form-control form-control--with-icon"
              id={`${prefix}-phone`}
              type="tel"
              placeholder="+543564123456"
              value={form.phone}
              onChange={(event) => update('phone', event.target.value)}
              minLength={6}
              maxLength={30}
              pattern="\+?[0-9\s\-]{6,30}"
              required
            />
          </div>
        </div>

        <div className="form-field user-modal-form__full">
          <label htmlFor={`${prefix}-email`}>Email</label>
          <div className="input-control">
            <Mail className="input-control__icon" size={18} aria-hidden="true" />
            <input
              className="form-control form-control--with-icon"
              id={`${prefix}-email`}
              type="email"
              placeholder="carlos.gomez@empresa.com"
              value={form.email}
              onChange={(event) => update('email', event.target.value)}
              required
            />
          </div>
        </div>

        <div className="form-field user-modal-form__full">
          <label htmlFor={`${prefix}-role`}>Rol</label>
          <div className="input-control">
            <Shield className="input-control__icon" size={18} aria-hidden="true" />
            <select
              className="form-control form-control--with-icon"
              id={`${prefix}-role`}
              value={form.roleId}
              onChange={(event) => update('roleId', event.target.value === '' ? '' : Number(event.target.value))}
              disabled={rolesLoading || isSelf}
              required
            >
              <option value="" disabled>
                {rolesLoading ? 'Cargando roles…' : 'Seleccioná un rol'}
              </option>
              {options.map((role) => (
                <option key={role.id} value={role.id}>
                  {roleLabel(role.name)}
                </option>
              ))}
            </select>
          </div>
          <span className="user-modal-form__hint">
            <Info size={14} aria-hidden="true" />
            {isSelf
              ? 'No podés cambiar tu propio rol. Pedíselo a otro superadministrador.'
              : (selectedRole?.description ?? 'Define a qué secciones del sistema accede.')}
          </span>
        </div>
      </div>

      {error ? (
        <p className="form-error" role="alert">
          <Info size={18} aria-hidden="true" />
          {error}
        </p>
      ) : null}

      <div className="user-modal-form__actions">
        <button className="btn btn--ghost" type="button" onClick={onClose}>
          Cancelar
        </button>
        <button className="btn btn--primary" type="submit" disabled={pending || form.roleId === ''}>
          {pending ? (
            <LoaderCircle className="loading-icon" size={18} aria-hidden="true" />
          ) : employee ? (
            <Save size={18} aria-hidden="true" />
          ) : (
            <UserPlus size={18} aria-hidden="true" />
          )}
          {pending ? 'Guardando…' : employee ? 'Guardar cambios' : 'Registrar usuario'}
        </button>
      </div>
    </form>
  )
}
