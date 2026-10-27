export function receiverIsOldEnough(birthDate: string, today = new Date().toISOString().slice(0, 10)): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(birthDate)) return false
  const parsed = new Date(`${birthDate}T00:00:00Z`)
  if (!Number.isFinite(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== birthDate) return false
  const [year, month, day] = birthDate.split('-').map(Number)
  const [currentYear, currentMonth, currentDay] = today.split('-').map(Number)
  const age = currentYear - year - (currentMonth < month || (currentMonth === month && currentDay < day) ? 1 : 0)
  const anniversary = `${year + 16}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
  return birthDate <= today && anniversary < today && age <= 120
}
