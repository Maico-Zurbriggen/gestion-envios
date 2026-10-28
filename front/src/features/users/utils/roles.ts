const ROLE_LABELS: Record<string, string> = {
  SUPERADMIN: 'Superadministrador',
  ADMINISTRATIVO: 'Administrativo',
  VENDEDOR: 'Vendedor',
  REPARTIDOR: 'Repartidor',
}

export function roleLabel(role: string) {
  return ROLE_LABELS[role] ?? role.charAt(0) + role.slice(1).toLowerCase()
}

export function initials(name: string) {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  return ((parts[0]?.[0] ?? '') + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase() || 'U'
}
