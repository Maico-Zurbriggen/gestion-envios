import { ArrowLeft, LogIn, Moon, PackageCheck, Sun } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAppSelector } from '../../app/store'
import { selectIsAuthenticated } from '../../features/auth/redux/authSlice'
import { useTheme } from '../hooks/useTheme'
import './PublicHeader.css'

/** Encabezado de las páginas públicas (registro, seguimiento y preguntas frecuentes) fuera del panel. */
export function PublicHeader() {
  const isAuthenticated = useAppSelector(selectIsAuthenticated)
  const { theme, toggleTheme } = useTheme()
  const home = isAuthenticated ? '/' : '/login'

  return (
    <header className="public-header">
      <Link className="public-header__brand" to={home}>
        <span aria-hidden="true"><PackageCheck size={22} /></span>
        <strong>Gestión de envíos</strong>
      </Link>
      <div className="public-header__actions">
        <button type="button" onClick={toggleTheme} aria-label="Cambiar tema">
          {theme === 'light' ? <Moon size={19} aria-hidden="true" /> : <Sun size={19} aria-hidden="true" />}
        </button>
        <Link to={home} aria-label={isAuthenticated ? 'Volver al panel' : 'Iniciar sesión'}>
          {isAuthenticated ? <ArrowLeft size={18} aria-hidden="true" /> : <LogIn size={18} aria-hidden="true" />}
          <span>{isAuthenticated ? 'Volver al panel' : 'Ingresar'}</span>
        </Link>
      </div>
    </header>
  )
}
