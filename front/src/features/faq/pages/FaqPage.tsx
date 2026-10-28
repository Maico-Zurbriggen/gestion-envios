import { useState, type FormEvent } from 'react'
import {
  ArrowLeft, ArrowRight, ArrowUpRight, ChevronLeft, ChevronRight, CircleAlert, CircleHelp, ListFilter,
  LoaderCircle, LogIn, MapPin, Moon, PackageCheck, RefreshCw, Search, Sun, X,
} from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import { useAppSelector } from '../../../app/store'
import { useTheme } from '../../../shared/hooks/useTheme'
import { useInsidePanel } from '../../../layouts/MainLayout/panelContext'
import { selectIsAuthenticated } from '../../auth/redux/authSlice'
import { useFaqs } from '../hooks/useFaqs'
import type { FaqQuestion } from '../types/faq.types'
import { Modal } from '../../../shared/components/Modal'
import './FaqPage.css'

function normalizeCategory(value: string) {
  return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('es-AR').trim()
}

function FaqSearch({ search, hasFilters, pending, onSearch, onClear }: {
  search: string
  hasFilters: boolean
  pending: boolean
  onSearch: (value: string) => void
  onClear: () => void
}) {
  const [input, setInput] = useState(search)

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onSearch(input.trim())
  }

  return (
    <form className="faq-search" role="search" onSubmit={handleSubmit} onReset={() => { setInput(''); onClear() }}>
      <label htmlFor="faq-search">Buscá tu consulta</label>
      <div className="faq-search__controls">
        <div className="input-control">
          <Search size={19} className="input-control__icon" aria-hidden="true" />
          <input className="form-control form-control--with-icon" id="faq-search" type="search"
            value={input} onChange={(event) => setInput(event.target.value)} maxLength={100}
            placeholder="Por ejemplo: peso, seguimiento o retiro" autoComplete="off" />
        </div>
        <button className="faq-button faq-button--primary" type="submit" disabled={pending}>
          {pending ? <LoaderCircle className="loading-icon" size={18} aria-hidden="true" /> : <Search size={18} aria-hidden="true" />}
          Buscar
        </button>
      </div>
      {(hasFilters || input) && <button className="faq-search__clear" type="reset"><X size={16} aria-hidden="true" /> Limpiar filtros</button>}
    </form>
  )
}

export function FaqPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const search = (searchParams.get('q') ?? '').trim().slice(0, 100)
  const category = (searchParams.get('categoria') ?? '').trim().slice(0, 80)
  const query = useFaqs({ search, category })
  const isAuthenticated = useAppSelector(selectIsAuthenticated)
  const insidePanel = useInsidePanel()
  const { theme, toggleTheme } = useTheme()
  const loading = query.isPending || query.isPlaceholderData
  const hasFilters = Boolean(search || category)
  const listing = !query.isPlaceholderData ? query.data : undefined
  const totalQuestions = query.data?.categories.reduce((total, item) => total + item.count, 0) ?? 0
  const groups = new Map<string, FaqQuestion[]>()
  for (const question of listing?.questions ?? []) {
    const questions = groups.get(question.category) ?? []
    questions.push(question)
    groups.set(question.category, questions)
  }
  const ordered = Array.from(groups.values()).flat()
  const [openId, setOpenId] = useState<FaqQuestion['id'] | null>(null)
  const openIndex = ordered.findIndex((question) => question.id === openId)
  const openQuestion = openIndex >= 0 ? ordered[openIndex] : undefined

  function updateFilters(nextSearch: string, nextCategory: string) {
    const params = new URLSearchParams()
    if (nextSearch) params.set('q', nextSearch)
    if (nextCategory) params.set('categoria', nextCategory)
    setSearchParams(params)
  }

  return (
    <main className={`faq-page${insidePanel ? ' is-embedded' : ''}`}>
      {!insidePanel && <header className="faq-public-header">
        <Link className="faq-brand" to={isAuthenticated ? '/' : '/login'}>
          <span aria-hidden="true"><PackageCheck size={22} /></span><strong>Gestión de envíos</strong>
        </Link>
        <div className="faq-public-header__actions">
          <button type="button" onClick={toggleTheme} aria-label="Cambiar tema">
            {theme === 'light' ? <Moon size={19} aria-hidden="true" /> : <Sun size={19} aria-hidden="true" />}
          </button>
          <Link to={isAuthenticated ? '/' : '/login'} aria-label={isAuthenticated ? 'Volver al panel' : 'Iniciar sesión'}>
            {isAuthenticated ? <ArrowLeft size={18} aria-hidden="true" /> : <LogIn size={18} aria-hidden="true" />}
            <span>{isAuthenticated ? 'Volver al panel' : 'Ingresar'}</span>
          </Link>
        </div>
      </header>}

      <div className="faq-page__content">
        <header className="faq-hero">
          <span className="eyebrow"><CircleHelp size={16} aria-hidden="true" /> Centro de ayuda</span>
          <h1>Preguntas frecuentes</h1>
          <p>Encontrá respuestas sobre envíos, seguimiento y entregas. No necesitás iniciar sesión.</p>
        </header>
        <FaqSearch key={search} search={search} hasFilters={hasFilters} pending={query.isFetching}
          onSearch={(value) => {
            if (value === search) void query.refetch()
            else updateFilters(value, category)
          }} onClear={() => updateFilters('', '')} />

        <div className="faq-layout">
          <aside className="faq-topics" aria-labelledby="faq-topics-title">
            <h2 id="faq-topics-title"><ListFilter size={18} aria-hidden="true" /> Explorá por tema</h2>
            <div className="faq-topics__filters">
              <button type="button" aria-pressed={!category} onClick={() => updateFilters(search, '')}>
                <span>Todos los temas</span>{query.data && <small>{totalQuestions}</small>}
              </button>
              {query.data?.categories.map((item) => (
                <button key={item.name} type="button" aria-pressed={normalizeCategory(category) === normalizeCategory(item.name)} onClick={() => updateFilters(search, item.name)}>
                  <span>{item.name}</span><small>{item.count}</small>
                </button>
              ))}
            </div>
          </aside>

          <section className="faq-results" aria-label="Preguntas y respuestas" aria-busy={query.isFetching}>
            <p className="faq-results__count" role="status">
              {loading ? 'Cargando preguntas frecuentes…' : query.isError ? 'No pudimos actualizar las preguntas.'
                : `${listing?.total ?? 0} ${(listing?.total ?? 0) === 1 ? 'pregunta encontrada' : 'preguntas encontradas'}${search ? ` para “${search}”` : ''}${category ? ` en ${category}` : ''}.`}
            </p>

            {loading && <div className="faq-feedback" role="status"><LoaderCircle className="loading-icon" size={25} aria-hidden="true" /><p>Estamos buscando las respuestas.</p></div>}
            {query.isError && <div className="faq-feedback faq-feedback--error" role="alert">
              <CircleAlert size={25} aria-hidden="true" />
              <div><h2>No pudimos cargar las preguntas</h2><p>{query.error.message}</p>
                <button className="faq-button" type="button" disabled={query.isFetching} onClick={() => void query.refetch()}><RefreshCw size={17} aria-hidden="true" /> Reintentar</button>
              </div>
            </div>}

            {listing?.questions.length === 0 && !query.isError && <div className="faq-feedback">
              <CircleHelp size={28} aria-hidden="true" />
              <div><h2>{hasFilters ? 'No encontramos coincidencias' : 'Todavía no hay preguntas publicadas'}</h2>
                <p>{hasFilters ? 'Probá con otras palabras o consultá todos los temas.' : 'Volvé a consultar esta sección más adelante.'}</p>
                {hasFilters && <button className="faq-button" type="button" onClick={() => updateFilters('', '')}><X size={17} aria-hidden="true" /> Ver todas las preguntas</button>}
              </div>
            </div>}

            {Array.from(groups, ([name, questions]) => (
              <section className="faq-group" key={name} aria-label={name}>
                <h2>{name}</h2>
                <div className="faq-group__questions">
                  {questions.map((question) => (
                    <button className="faq-question" key={`${search}:${category}:${question.id}`} type="button" aria-haspopup="dialog" onClick={() => setOpenId(question.id)}>
                      <span className="faq-question__text">
                        <h3>{question.question}</h3>
                        <span className="faq-question__preview">{question.answer}</span>
                      </span>
                      <ArrowUpRight size={19} aria-hidden="true" />
                    </button>
                  ))}
                </div>
              </section>
            ))}
          </section>
        </div>

        <Modal
          open={openQuestion !== undefined}
          onClose={() => setOpenId(null)}
          eyebrow={openQuestion?.category}
          title={openQuestion?.question ?? ''}
          icon={CircleHelp}
          footer={<>
            <span className="faq-modal__position">{openIndex + 1} de {ordered.length}</span>
            <button className="faq-button" type="button" disabled={openIndex <= 0} onClick={() => setOpenId(ordered[openIndex - 1].id)}><ChevronLeft size={17} aria-hidden="true" /> Anterior</button>
            <button className="faq-button faq-button--primary" type="button" disabled={openIndex >= ordered.length - 1} onClick={() => setOpenId(ordered[openIndex + 1].id)}>Siguiente <ChevronRight size={17} aria-hidden="true" /></button>
          </>}
        >
          <p className="faq-modal__answer">{openQuestion?.answer}</p>
        </Modal>

        <footer className="faq-next-steps" aria-label="Otras consultas públicas">
          <div><h2>Consultá tu envío</h2><p>Seguí tus paquetes o iniciá un reclamo con tu código de seguimiento.</p></div>
          <Link className="faq-button faq-button--primary" to="/seguimiento"><Search size={17} aria-hidden="true" /> Seguir un envío <ArrowRight size={17} aria-hidden="true" /></Link>
          <Link className="faq-button" to="/sucursales"><MapPin size={17} aria-hidden="true" /> Ver sucursales</Link>
        </footer>
      </div>
    </main>
  )
}
