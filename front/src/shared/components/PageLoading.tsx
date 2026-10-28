import { LoaderCircle } from 'lucide-react'

/** Mientras se descarga una página que se carga a demanda. Sus estilos son globales (ui.css). */
export function PageLoading({ label }: { label: string }) {
  return (
    <p className="page-loading" role="status">
      <LoaderCircle className="loading-icon" size={20} aria-hidden="true" />
      {label}
    </p>
  )
}
