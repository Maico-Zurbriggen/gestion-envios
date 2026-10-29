import { Building2, Check, LogOut, MapPin } from 'lucide-react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { useAppDispatch, useAppSelector } from '../../../app/store'
import { requiresBranch } from '../branchAccess'
import { useActiveBranch } from '../hooks/useActiveBranch'
import { clearCredentials, selectCurrentUser } from '../redux/authSlice'
import { loadActiveBranch } from '../services/authStorage'
import './ChooseBranchPage.css'

/** Después del login: a qué sucursal entra. Solo aparecen las que tiene habilitadas. */
export function ChooseBranchPage() {
  const user = useAppSelector(selectCurrentUser)
  const { branches, choose } = useActiveBranch()
  const dispatch = useAppDispatch()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const location = useLocation()
  const destination = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? '/'

  if (!user || !requiresBranch(user.role)) return <Navigate to="/" replace />

  const lastUsed = loadActiveBranch(user.id)

  function enter(id: number) {
    choose(id)
    // Lo que estaba en pantalla era de otra sucursal.
    queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== 'auth' })
    navigate(destination === '/elegir-sucursal' ? '/' : destination, { replace: true })
  }

  function logout() {
    queryClient.clear()
    dispatch(clearCredentials())
    navigate('/login', { replace: true })
  }

  return (
    <main className="choose-branch">
      <section className="choose-branch__card" aria-labelledby="choose-branch-title">
        <span className="choose-branch__icon" aria-hidden="true"><Building2 size={28} /></span>
        <h1 id="choose-branch-title">¿En qué sucursal vas a trabajar?</h1>
        {branches.length ? (
          <>
            <p>Todo lo que cargues y veas va a ser de esa sucursal. Después la podés cambiar desde la barra de arriba.</p>
            <ul className="choose-branch__list">
              {branches.map((branch) => (
                <li key={branch.id}>
                  <button className="choose-branch__option" type="button" onClick={() => enter(branch.id)}>
                    <span className="choose-branch__name">
                      <strong>{branch.name}</strong>
                      {branch.id === lastUsed && <span className="badge">Última usada</span>}
                      {!branch.active && <span className="badge choose-branch__inactive">Inactiva</span>}
                    </span>
                    <span className="choose-branch__address">
                      <MapPin size={15} aria-hidden="true" /> {branch.address}, {branch.city}
                    </span>
                    <Check className="choose-branch__check" size={18} aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <p role="alert">
            Tu usuario todavía no tiene sucursales habilitadas. Pedile al Superadministrador que te habilite al menos una.
          </p>
        )}
        <button className="choose-branch__logout" type="button" onClick={logout}>
          <LogOut size={17} aria-hidden="true" /> Salir
        </button>
      </section>
    </main>
  )
}
