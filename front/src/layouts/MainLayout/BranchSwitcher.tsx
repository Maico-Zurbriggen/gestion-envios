import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react'
import { Building2, Check, ChevronDown, MapPin } from 'lucide-react'
import { useAppSelector } from '../../app/store'
import { requiresBranch } from '../../features/auth/branchAccess'
import { useActiveBranch } from '../../features/auth/hooks/useActiveBranch'
import { selectCurrentUser } from '../../features/auth/redux/authSlice'
import { showToast } from '../../shared/services/toast'

/** El ícono ya dice que es una sucursal: en la barra alcanza con el nombre propio. */
function shortName(name: string) {
  return name.replace(/^sucursal\s+/i, '')
}

/** Sucursal en la que se trabaja. Cambiarla cambia todo lo que se ve y se carga. */
export function BranchSwitcher() {
  const user = useAppSelector(selectCurrentUser)
  const { branch, branches, choose } = useActiveBranch()
  const [open, setOpen] = useState(false)
  const [focused, setFocused] = useState(0)
  const rootRef = useRef<HTMLDivElement>(null)
  const optionRefs = useRef<Array<HTMLButtonElement | null>>([])
  const listId = useId()

  useEffect(() => {
    if (!open) return
    function close(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [open])

  useEffect(() => {
    if (open) optionRefs.current[focused]?.focus()
  }, [open, focused])

  if (!requiresBranch(user?.role) || !branches.length) return null

  if (branches.length === 1) {
    return (
      <span className="branch-switcher branch-switcher--single" title="Sucursal en la que trabajás">
        <Building2 size={16} aria-hidden="true" />
        <span className="branch-switcher__name">{shortName(branches[0].name)}</span>
      </span>
    )
  }

  function openMenu() {
    setFocused(Math.max(0, branches.findIndex((item) => item.id === branch?.id)))
    setOpen(true)
  }

  function select(id: number) {
    setOpen(false)
    if (id === branch?.id) return
    choose(id)
    const next = branches.find((item) => item.id === id)
    if (next) showToast(`Ahora trabajás en ${next.name}.`)
  }

  function onListKeyDown(event: KeyboardEvent) {
    const last = branches.length - 1
    const moves: Record<string, number> = { ArrowDown: Math.min(last, focused + 1), ArrowUp: Math.max(0, focused - 1), Home: 0, End: last }
    if (event.key in moves) {
      event.preventDefault()
      setFocused(moves[event.key])
    } else if (event.key === 'Escape' || event.key === 'Tab') {
      setOpen(false)
      if (event.key === 'Escape') rootRef.current?.querySelector<HTMLButtonElement>('.branch-switcher__trigger')?.focus()
    }
  }

  return (
    <div className="branch-switcher" ref={rootRef}>
      <button
        type="button"
        className="branch-switcher__trigger"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? listId : undefined}
        title="Sucursal en la que trabajás"
        onClick={() => (open ? setOpen(false) : openMenu())}
        onKeyDown={(event) => {
          if (event.key === 'ArrowDown' && !open) {
            event.preventDefault()
            openMenu()
          }
        }}
      >
        <Building2 size={16} aria-hidden="true" />
        <span className="visually-hidden">Sucursal en la que trabajás: </span>
        <span className="branch-switcher__name">{branch ? shortName(branch.name) : 'Elegí una sucursal'}</span>
        <ChevronDown className="branch-switcher__chevron" size={16} aria-hidden="true" />
      </button>

      {open && (
        <div className="branch-switcher__menu" onKeyDown={onListKeyDown}>
          <p className="branch-switcher__heading">Trabajar en</p>
          <ul id={listId} role="listbox" aria-label="Sucursales habilitadas">
            {branches.map((item, index) => {
              const current = item.id === branch?.id
              return (
                <li key={item.id} role="presentation">
                  <button
                    ref={(element) => { optionRefs.current[index] = element }}
                    type="button"
                    role="option"
                    aria-selected={current}
                    tabIndex={index === focused ? 0 : -1}
                    className={`branch-switcher__option${current ? ' is-current' : ''}`}
                    onClick={() => select(item.id)}
                    onFocus={() => setFocused(index)}
                  >
                    <span className="branch-switcher__icon" aria-hidden="true"><Building2 size={16} /></span>
                    <span className="branch-switcher__text">
                      <strong>{shortName(item.name)}{item.active ? '' : ' · inactiva'}</strong>
                      <small><MapPin size={12} aria-hidden="true" /> {item.city}</small>
                    </span>
                    {current && <Check className="branch-switcher__check" size={16} aria-hidden="true" />}
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </div>
  )
}
