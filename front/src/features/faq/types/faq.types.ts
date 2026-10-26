export interface FaqSuccessResponse {
  status: 'success'
  data: {
    total: number
    categorias: Array<{ nombre: string; cantidad: number }>
    preguntas: Array<{
      id: number
      categoria: string
      pregunta: string
      respuesta: string
      orden: number
    }>
  }
}

export interface FaqErrorResponse {
  code?: string
  message?: string
  errors?: Array<{ field?: string; message?: string }>
}

export interface FaqQuestion {
  id: number
  category: string
  question: string
  answer: string
  order: number
}

export interface FaqListing {
  total: number
  categories: Array<{ name: string; count: number }>
  questions: FaqQuestion[]
}

export interface FaqFilters {
  category: string
  search: string
}
