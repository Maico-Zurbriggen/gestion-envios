/**
 * Impresión de documentos armados como HTML (portado de Soderia-ERP).
 */

/**
 * Escapa texto para insertarlo en HTML armado a mano. Sin esto, un nombre con
 * código HTML se interpretaría al imprimir la etiqueta.
 */
export function escapeHtml(value: unknown): string {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

/** Política de contenido del documento impreso: ningún script puede ejecutarse. */
export const PRINT_CSP = "default-src 'none'; img-src data: blob:; style-src 'unsafe-inline'; font-src data:"

const CLEANUP_FALLBACK_MS = 60_000

/**
 * Imprime HTML en un iframe oculto y aislado (sin scripts ni acceso a la
 * sesión) y lo retira cuando se cierra el diálogo de impresión.
 */
export function printHtml(html: string): void {
  const iframe = document.createElement('iframe')
  // Sin `allow-scripts`: aunque algo se escapara, no podría ejecutarse.
  iframe.setAttribute('sandbox', 'allow-modals allow-same-origin')
  iframe.setAttribute('aria-hidden', 'true')
  iframe.tabIndex = -1
  Object.assign(iframe.style, { position: 'fixed', right: '0', bottom: '0', width: '0', height: '0', border: '0' })
  document.body.appendChild(iframe)

  const doc = iframe.contentDocument
  const win = iframe.contentWindow
  if (!doc || !win) {
    iframe.remove()
    throw new Error('No se pudo preparar la impresión.')
  }

  const csp = `<meta http-equiv="Content-Security-Policy" content="${PRINT_CSP}">`
  doc.open()
  doc.write(html.replace(/<head>/i, `<head>${csp}`))
  doc.close()

  let removed = false
  const cleanup = () => {
    if (removed) return
    removed = true
    iframe.remove()
  }
  win.addEventListener('afterprint', () => window.setTimeout(cleanup, 500))
  window.setTimeout(cleanup, CLEANUP_FALLBACK_MS)
  // Una pausa breve deja que el navegador maquete las páginas antes de imprimir.
  window.setTimeout(() => {
    try {
      win.focus()
      win.print()
    } catch {
      cleanup()
    }
  }, 300)
}
