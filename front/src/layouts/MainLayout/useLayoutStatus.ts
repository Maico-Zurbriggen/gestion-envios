import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'

/** Consulta liviana al /health de la API para mostrar si el servidor responde. */
export function useApiStatus() {
  return useQuery({
    queryKey: ['api-health'],
    queryFn: async ({ signal }) => {
      const apiUrl = import.meta.env.VITE_API_URL?.replace(/\/+$/, '')
      if (!apiUrl) return false
      try {
        const response = await fetch(`${apiUrl}/health`, { signal, cache: 'no-store' })
        return response.ok
      } catch {
        return false
      }
    },
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
    retry: false,
  })
}

/** Hora actual, actualizada cada 30 segundos. */
export function useNow() {
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 30_000)
    return () => window.clearInterval(timer)
  }, [])
  return now
}

const COLLAPSED_KEY = 'gestion-envios.sidebar-colapsada'

export function readSidebarCollapsed() {
  try {
    return localStorage.getItem(COLLAPSED_KEY) === '1'
  } catch {
    return false
  }
}

export function storeSidebarCollapsed(collapsed: boolean) {
  try {
    localStorage.setItem(COLLAPSED_KEY, collapsed ? '1' : '0')
  } catch {
    // Sin almacenamiento disponible: solo dura la sesión actual.
  }
}
