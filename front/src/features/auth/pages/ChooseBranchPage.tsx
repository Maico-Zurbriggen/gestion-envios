import { useState } from 'react'
import { Building2, ChevronRight, History, LogOut, MapPin, PackageCheck, Search, ShieldCheck } from 'lucide-react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { useAppDispatch, useAppSelector } from '../../../app/store'
import { roleLabel } from '../../../shared/utils/roles'
import { requiresBranch } from '../branchAccess'
import { useActiveBranch } from '../hooks/useActiveBranch'
import { clearCredentials, selectCurrentUser } from '../redux/authSlice'
import { loadActiveBranch } from '../services/authStorage'
import './LoginPage.css'
import './ChooseBranchPage.css'

/** Con más sucursales que estas, aparece el buscador. */
const SEARCH_FROM = 6

/** El ícono y el título ya dicen que es una sucursal: alcanza con el nombre propio. */
function shortName(name: string) {
  return name.replace(/^sucursal\s+/i, '')
}

function normalize(value: string) {
  return value.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
}

/** Después del login: a qué sucursal entra. Solo aparecen las que tiene habilitadas. */
export function ChooseBranchPage() {
  const user = useAppSelector(selectCurrentUser)
  const { branches, choose } = useActiveBranch()
  const dispatch = useAppDispatch()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const location = useLocation()
  const [query, setQuery] = useState('')
  const destination = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? '/'

  if (!user || !requiresBranch(user.role)) return <Navigate to="/" replace />

  const lastUsed = loadActiveBranch(user.id)
  const firstName = user.name?.trim().split(/\s+/)[0]
  // La última usada va primero; el resto, por nombre.
  const ordered = [...branches].sort((a, b) => Number(b.id === lastUsed) - Number(a.id === lastUsed) || a.name.localeCompare(b.name))
  const term = normalize(query.trim())
  const visible = term
    ? ordered.filter((branch) => normalize(`${branch.name} ${branch.city} ${branch.province} ${branch.address}`).includes(term))
    : ordered

  function enter(id: number) {
    choose(id)
    // Lo que estaba en pantalla era de otra sucursal.
    queryClient.removeQueries({ predicate: (cached) => cached.queryKey[0] !== 'auth' })
    navigate(destination === '/elegir-sucursal' ? '/' : destination, { replace: true })
  }

  function logout() {
    queryClient.clear()
    dispatch(clearCredentials())
    navigate('/login', { replace: true })
  }

  return (
    <main className="login-page choose-branch">
      <section className="login-card choose-branch__card" aria-labelledby="choose-branch-title">
        <aside className="login-brand">
          <div className="login-brand__identity">
            <span className="login-brand__mark" aria-hidden="true">
              <PackageCheck size={24} strokeWidth={2.25} />
            </span>
            <span>Gestión de envíos</span>
          </div>

          <div className="login-brand__content">
            <h2>{firstName ? `Hola, ${firstName}.` : 'Hola.'} <span>Elegí dónde trabajás hoy</span>.</h2>
            <p>Los paquetes que recibas, los recorridos que armes y lo que veas en el monitor van a ser de esa sucursal.</p>
          </div>

          <span className="login-brand__footer">
            <ShieldCheck size={17} aria-hidden="true" />
            {roleLabel(user.role)} · {branches.length} {branches.length === 1 ? 'sucursal habilitada' : 'sucursales habilitadas'}
          </span>
        </aside>

        <div className="login-panel choose-branch__panel">
          <header className="login-panel__header choose-branch__header">
            <span className="eyebrow">Último paso</span>
            <h1 id="choose-branch-title">Elegí la sucursal</h1>
            <p>Podés cambiarla cuando quieras desde la barra superior.</p>
          </header>

          {branches.length > SEARCH_FROM && (
            <div className="input-control choose-branch__search">
              <Search className="input-control__icon" size={18} aria-hidden="true" />
              <label className="visually-hidden" htmlFor="choose-branch-search">Buscar sucursal</label>
              <input
                className="form-control form-control--with-icon"
                id="choose-branch-search"
                type="search"
                placeholder="Buscar por nombre o ciudad"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                autoComplete="off"
              />
            </div>
          )}

          {branches.length === 0 ? (
            <div className="choose-branch__empty" role="alert">
              <Building2 size={26} aria-hidden="true" />
              <strong>Todavía no tenés sucursales habilitadas</strong>
              <p>Pedile al Superadministrador que te habilite al menos una desde Usuarios.</p>
            </div>
          ) : visible.length === 0 ? (
            <p className="choose-branch__none" role="status">Ninguna sucursal coincide con «{query.trim()}».</p>
          ) : (
            <ul className="choose-branch__list" aria-label="Sucursales habilitadas">
              {visible.map((branch) => {
                const last = branch.id === lastUsed
                return (
                  <li key={branch.id}>
                    <button className={`choose-branch__option${last ? ' is-last' : ''}`} type="button" onClick={() => enter(branch.id)}>
                      <span className="choose-branch__icon" aria-hidden="true"><Building2 size={20} /></span>
                      <span className="choose-branch__text">
                        <span className="choose-branch__name">
                          <strong>{shortName(branch.name)}</strong>
                          {last && <span className="choose-branch__tag"><History size={12} aria-hidden="true" /> Última usada</span>}
                          {!branch.active && <span className="choose-branch__tag choose-branch__tag--off">Inactiva</span>}
                        </span>
                        <span className="choose-branch__address">
                          <MapPin size={14} aria-hidden="true" />
                          <span>{branch.address} · {branch.city}{branch.province && branch.province !== branch.city ? `, ${branch.province}` : ''}</span>
                        </span>
                      </span>
                      <ChevronRight className="choose-branch__arrow" size={20} aria-hidden="true" />
                    </button>
                  </li>
                )
              })}
            </ul>
          )}

          <footer className="choose-branch__footer">
            <span>Ingresaste como <strong>{user.name ?? `DNI ${user.dni}`}</strong></span>
            <button className="choose-branch__logout" type="button" onClick={logout}>
              <LogOut size={16} aria-hidden="true" /> Salir
            </button>
          </footer>
        </div>
      </section>
    </main>
  )
}
