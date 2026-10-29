import { Building2 } from 'lucide-react'
import { useAppSelector } from '../../app/store'
import { requiresBranch } from '../../features/auth/branchAccess'
import { useActiveBranch } from '../../features/auth/hooks/useActiveBranch'
import { selectCurrentUser } from '../../features/auth/redux/authSlice'

/** El ícono ya dice que es una sucursal: en la barra alcanza con el nombre propio. */
function shortName(name: string) {
  return name.replace(/^sucursal\s+/i, '')
}

/** Sucursal en la que se trabaja. Cambiarla cambia todo lo que se ve y se carga. */
export function BranchSwitcher() {
  const user = useAppSelector(selectCurrentUser)
  const { branch, branches, choose } = useActiveBranch()

  if (!requiresBranch(user?.role) || !branches.length) return null

  if (branches.length === 1) {
    return (
      <span className="topbar-branch" title="Sucursal en la que trabajás">
        <Building2 size={16} aria-hidden="true" />
        <span className="topbar-branch__name">{shortName(branches[0].name)}</span>
      </span>
    )
  }

  return (
    <label className="topbar-branch" title="Sucursal en la que trabajás">
      <Building2 size={16} aria-hidden="true" />
      <span className="visually-hidden">Sucursal en la que trabajás</span>
      <select value={branch?.id ?? ''} onChange={(event) => choose(Number(event.target.value))}>
        {!branch && <option value="">Elegí una sucursal</option>}
        {branches.map((item) => (
          <option key={item.id} value={item.id}>{shortName(item.name)}{item.active ? '' : ' (inactiva)'}</option>
        ))}
      </select>
    </label>
  )
}
