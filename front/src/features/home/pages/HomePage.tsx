import {
  ArrowRight,
  BadgeCheck,
  Boxes,
  Construction,
  IdCard,
  ShieldCheck,
  Sparkles,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { getAccessibleModules } from '../../../app/navigation'
import { useAppSelector } from '../../../app/store'
import { selectCurrentUser } from '../../auth/redux/authSlice'
import './HomePage.css'

export function HomePage() {
  const user = useAppSelector(selectCurrentUser)
  const accessibleModules = getAccessibleModules(user?.role)
  const quickAccessModules = accessibleModules.filter(
    (module) => module.showAsQuickAccess,
  )
  const firstName = user?.name?.trim().split(/\s+/)[0]

  return (
    <main className="home-page">
      <section className="home-hero">
        <div>
          <span className="eyebrow">
            <Sparkles size={14} aria-hidden="true" />
            Panel principal
          </span>
          <h1>{firstName ? `Hola, ${firstName}` : 'Bienvenido'}</h1>
          <p>
            Desde acá podés acceder rápidamente a las herramientas habilitadas
            para tu perfil.
          </p>
        </div>
        <span className="home-role-badge">
          <BadgeCheck size={17} aria-hidden="true" />
          {user?.role || 'Usuario'}
        </span>
      </section>

      <section className="home-overview" aria-label="Resumen de la cuenta">
        <article className="overview-card">
          <span className="overview-card__icon" aria-hidden="true">
            <ShieldCheck size={21} />
          </span>
          <div>
            <small>Estado de sesión</small>
            <strong>Protegida y activa</strong>
          </div>
        </article>
        <article className="overview-card">
          <span className="overview-card__icon" aria-hidden="true">
            <IdCard size={21} />
          </span>
          <div>
            <small>DNI de la cuenta</small>
            <strong>{user?.dni || 'No disponible'}</strong>
          </div>
        </article>
        <article className="overview-card">
          <span className="overview-card__icon" aria-hidden="true">
            <Boxes size={21} />
          </span>
          <div>
            <small>Módulos habilitados</small>
            <strong>{quickAccessModules.length}</strong>
          </div>
        </article>
      </section>

      <section className="quick-access" aria-labelledby="quick-access-title">
        <header className="quick-access__header">
          <div>
            <span className="eyebrow">Tu espacio de trabajo</span>
            <h2 id="quick-access-title">Accesos rápidos</h2>
          </div>
          <p>Sólo se muestran los módulos disponibles para tu rol.</p>
        </header>

        {quickAccessModules.length ? (
          <div className="quick-access__grid">
            {quickAccessModules.map((module) => {
              const Icon = module.icon

              return (
                <Link className="module-card" key={module.id} to={module.path}>
                  <span className="module-card__icon" aria-hidden="true">
                    <Icon size={23} />
                  </span>
                  <span className="module-card__content">
                    <strong>{module.label}</strong>
                    <small>{module.description}</small>
                  </span>
                  <ArrowRight
                    className="module-card__arrow"
                    size={19}
                    aria-hidden="true"
                  />
                </Link>
              )
            })}
          </div>
        ) : (
          <div className="quick-access-empty">
            <span aria-hidden="true">
              <Construction size={25} />
            </span>
            <div>
              <strong>No hay módulos operativos publicados para tu rol todavía.</strong>
              <p>
                Tu acceso está activo. Las nuevas herramientas aparecerán acá
                cuando estén disponibles.
              </p>
            </div>
          </div>
        )}
      </section>

      <aside className="security-tip">
        <ShieldCheck size={20} aria-hidden="true" />
        <div>
          <strong>Protegé tu cuenta</strong>
          <p>
            No compartas tu contraseña ni la dejes guardada en equipos de uso
            compartido. Cerrá la sesión al terminar.
          </p>
        </div>
      </aside>
    </main>
  )
}
