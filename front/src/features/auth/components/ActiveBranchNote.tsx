import { Building2 } from 'lucide-react'
import { useActiveBranch } from '../hooks/useActiveBranch'

/** Recuerda en qué sucursal se está operando; se cambia desde la barra superior. */
export function ActiveBranchNote({ action }: { action: string }) {
  const { branch } = useActiveBranch()
  if (!branch) return null
  return (
    <p className="active-branch-note">
      <Building2 size={17} aria-hidden="true" />
      <span>{action} <strong>{branch.name}</strong></span>
    </p>
  )
}
