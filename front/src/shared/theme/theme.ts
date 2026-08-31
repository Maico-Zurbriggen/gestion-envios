export type AppTheme = 'light' | 'dark'

const THEME_STORAGE_KEY = 'gestion-envios.theme'

export function getInitialTheme(): AppTheme {
  const storedTheme = localStorage.getItem(THEME_STORAGE_KEY)
  if (storedTheme === 'light' || storedTheme === 'dark') return storedTheme

  return window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light'
}

export function applyTheme(theme: AppTheme) {
  document.documentElement.dataset.theme = theme
  document.documentElement.style.colorScheme = theme
  localStorage.setItem(THEME_STORAGE_KEY, theme)
}
