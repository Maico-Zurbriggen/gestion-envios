import { useEffect, useState } from 'react'
import {
  applyTheme,
  getInitialTheme,
  type AppTheme,
} from '../theme/theme'

export function useTheme() {
  const [theme, setTheme] = useState<AppTheme>(getInitialTheme)

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  return {
    theme,
    toggleTheme: () => setTheme((current) => (current === 'light' ? 'dark' : 'light')),
  }
}
