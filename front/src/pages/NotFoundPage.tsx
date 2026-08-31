import { Link } from 'react-router-dom'
import { useAppSelector } from '../app/store'
import { selectIsAuthenticated } from '../features/auth/authSlice'
import '../App.css'

export function NotFoundPage() {
  const isAuthenticated = useAppSelector(selectIsAuthenticated)
  const destination = isAuthenticated ? '/' : '/login'

  return (
    <main className="page-shell">
      <span className="eyebrow">Error 404</span>
      <h1>Ruta no encontrada</h1>
      <p>La dirección ingresada no existe o fue movida.</p>
      <Link className="page-action" to={destination} replace>
        {isAuthenticated ? 'Volver al inicio' : 'Ir a iniciar sesión'}
      </Link>
    </main>
  )
}
