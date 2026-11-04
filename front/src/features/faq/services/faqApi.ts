import type { FaqErrorResponse, FaqFilters, FaqListing, FaqSuccessResponse } from '../types/faq.types'

const apiUrl = import.meta.env.VITE_API_URL?.replace(/\/+$/, '')

export class FaqApiError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'FaqApiError'
  }
}

export async function getFaqs(filters: FaqFilters, signal?: AbortSignal): Promise<FaqListing> {
  const listing = await requestFaqs(filters, signal)
  if (listing.total > 0 || !filters.search) return listing

  const normalizedSearch = filters.search.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('es-AR')
  const relatedSearch = normalizedSearch.replace(/\bpesos?\b/g, 'pesar')
  if (relatedSearch === normalizedSearch) return listing

  return requestFaqs({ ...filters, search: relatedSearch }, signal)
}

async function requestFaqs(filters: FaqFilters, signal?: AbortSignal): Promise<FaqListing> {
  if (!apiUrl) throw new FaqApiError('No se configuró la URL de la API.')
  const params = new URLSearchParams()
  if (filters.category) params.set('categoria', filters.category)
  if (filters.search) params.set('q', filters.search)
  const query = params.toString()
  let response: Response
  try {
    response = await fetch(`${apiUrl}/preguntas-frecuentes${query ? `?${query}` : ''}`, {
      headers: { Accept: 'application/json' },
      signal,
    })
  } catch (error) {
    if (signal?.aborted) throw error
    throw new FaqApiError('No pudimos conectarnos. Revisá tu conexión e intentá nuevamente.')
  }
  const payload: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const error = payload as FaqErrorResponse | null
    if (response.status === 400 || response.status === 422) {
      const invalidSearch = Array.isArray(error?.errors) && error.errors.some((issue) => issue?.field === 'q')
      throw new FaqApiError(invalidSearch
        ? 'La búsqueda admite hasta 100 caracteres. Acortá el texto e intentá nuevamente.'
        : 'No pudimos aplicar los filtros. Limpiá la búsqueda e intentá nuevamente.')
    }
    throw new FaqApiError('Las preguntas frecuentes no están disponibles en este momento. Intentá nuevamente más tarde.')
  }
  const result = payload as FaqSuccessResponse | null
  const data = result?.data
  if (result?.status !== 'success' || !data || !Number.isInteger(data.total) || data.total < 0 ||
    !Array.isArray(data.categorias) || !Array.isArray(data.preguntas) ||
    !data.categorias.every((category) => category && typeof category.nombre === 'string' && Number.isInteger(category.cantidad) && category.cantidad >= 0) ||
    !data.preguntas.every((question) => question && Number.isInteger(question.id) && typeof question.categoria === 'string' &&
      typeof question.pregunta === 'string' && typeof question.respuesta === 'string')) {
    throw new FaqApiError('No pudimos cargar el contenido de las preguntas frecuentes. Intentá nuevamente.')
  }
  return {
    total: data.total,
    categories: data.categorias.map((category) => ({ name: category.nombre, count: category.cantidad })),
    questions: data.preguntas.map((question) => ({
      id: question.id, category: question.categoria, question: question.pregunta,
      answer: question.respuesta, order: question.orden,
    })),
  }
}
