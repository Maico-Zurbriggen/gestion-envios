/** La API en SQLite devuelve fechas sin zona horaria: siempre son UTC. */
export function parseApiDate(value: string) {
  return new Date(/[zZ]|[+-]\d{2}:?\d{2}$/.test(value) ? value : `${value}Z`)
}

const longDay = new Intl.DateTimeFormat('es-AR', { weekday: 'long', day: 'numeric', month: 'long' })
const shortDay = new Intl.DateTimeFormat('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' })

/** «viernes, 6 de noviembre»: para plazos como el de retiro. */
export function formatLongDay(value: string) {
  return longDay.format(parseApiDate(value))
}

/** «06/11/2026», en hora local. */
export function formatShortDay(value: string) {
  return shortDay.format(parseApiDate(value))
}
