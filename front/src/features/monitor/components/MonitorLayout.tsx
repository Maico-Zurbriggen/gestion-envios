import { Outlet } from 'react-router-dom'
import '../monitor.css'

/**
 * Marco de la sección Monitor. Como en TamboApp, las subsecciones se eligen
 * desde el menú lateral: cada pantalla abre con su propio encabezado.
 */
export function MonitorLayout() {
  return (
    <div className="monitor-area">
      <Outlet />
    </div>
  )
}
