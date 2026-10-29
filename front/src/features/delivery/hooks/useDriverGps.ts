import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useAppSelector } from '../../../app/store'
import { selectAuthToken } from '../../auth/redux/authSlice'
import { OperationalApiError } from '../../../shared/services/operationalApi'
import { sendPosition } from '../services/deliveryApi'

export function useDriverGps(id: string, active: boolean) {
  const token = useAppSelector(selectAuthToken)
  const client = useQueryClient()
  const [enabled, setEnabled] = useState(false)
  const [error, setError] = useState('')
  const [sending, setSending] = useState(false)
  useEffect(() => {
    if (!enabled || !active || !token) return
    let disposed = false
    let busy = false
    let lastSent = 0
    const controller = new AbortController()
    const watch = navigator.geolocation.watchPosition(async ({ coords }) => {
      if (disposed || busy || Date.now() - lastSent < 10000) return
      busy = true; lastSent = Date.now(); setSending(true)
      try {
        const result = await sendPosition(id, coords.latitude, coords.longitude, token, controller.signal)
        if (disposed) return
        setError('')
        client.setQueryData(['delivery', 'position', id], result.position)
      } catch (issue) {
        if (disposed) return
        setError(issue instanceof Error ? issue.message : 'No pudimos enviar la ubicación.')
        if (issue instanceof OperationalApiError && [400, 401, 403, 404].includes(issue.status ?? 0)) { setEnabled(false); void client.invalidateQueries({ queryKey: ['delivery'] }) }
      } finally { busy = false; if (!disposed) setSending(false) }
    }, (issue) => {
      if (disposed) return
      setError(issue.code === 1 ? 'Permiso de ubicación denegado. Habilitalo en la configuración del navegador y volvé a activar el GPS.' : 'No pudimos obtener una ubicación precisa. Revisá el GPS y volvé a activarlo.')
      setEnabled(false)
    }, { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 })
    return () => { disposed = true; controller.abort(); navigator.geolocation.clearWatch(watch) }
  }, [enabled, active, id, token, client])
  function toggle() {
    setError(''); setSending(false)
    if (enabled) { setEnabled(false); return }
    if (!window.isSecureContext) { setError('La ubicación requiere abrir la aplicación con HTTPS o en localhost.'); return }
    if (!navigator.geolocation) { setError('Este navegador no ofrece ubicación.'); return }
    setEnabled(true)
  }
  return { enabled: enabled && active, sending: sending && active && enabled, error, toggle }
}
