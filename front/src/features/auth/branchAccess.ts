import type { AuthBranch, AuthUser } from './types/auth.types'

/** El repartidor sale siempre de su sucursal base: no elige sucursal al ingresar. */
export function requiresBranch(role: string | null | undefined) {
  return Boolean(role) && role !== 'REPARTIDOR'
}

/** Mantiene la sucursal anterior si sigue habilitada; con una sola, entra directo en esa. */
export function resolveActiveBranch(branches: AuthBranch[], previousId: number | null) {
  if (previousId !== null && branches.some((branch) => branch.id === previousId)) return previousId
  return branches.length === 1 ? branches[0].id : null
}

/** Después del login se pregunta a qué sucursal ingresar cuando tiene más de una. */
export function shouldChooseBranch(user: AuthUser) {
  return requiresBranch(user.role) && user.branches.length > 1
}
