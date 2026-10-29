/**
 * Mientras se descarga o prepara una sección: el esqueleto de la pantalla que viene
 * (encabezado, indicadores y lista) con brillo animado. Sus estilos son globales (ui.css).
 */
export function PageLoading({ label }: { label: string }) {
  return (
    <div className="page-loading" role="status" aria-live="polite">
      <span className="visually-hidden">{label}</span>
      <div className="page-loading__header" aria-hidden="true">
        <span className="skeleton page-loading__icon" />
        <div>
          <span className="skeleton page-loading__title" />
          <span className="skeleton page-loading__text" />
        </div>
      </div>
      <div className="page-loading__cards" aria-hidden="true">
        {[0, 1, 2, 3].map((item) => <span key={item} className="skeleton page-loading__card" />)}
      </div>
      <div className="page-loading__list" aria-hidden="true">
        {[0, 1, 2, 3, 4].map((item) => (
          <div key={item} className="page-loading__row">
            <span className="skeleton page-loading__avatar" />
            <span className="skeleton page-loading__line" style={{ width: `${70 - item * 8}%` }} />
          </div>
        ))}
      </div>
    </div>
  )
}
