import { Link } from 'react-router-dom'
import '../App.css'

export function UnauthorizedPage() {
  return (
    <main className="page-shell">
      <span className="eyebrow">Error 403</span>
      <h1>Acceso no autorizado</h1>
      <p>Tu usuario no cuenta con los permisos necesarios para esta ruta.</p>
      <Link className="page-action" to="/" replace>
        Volver al inicio
      </Link>
    </main>
  )
}
