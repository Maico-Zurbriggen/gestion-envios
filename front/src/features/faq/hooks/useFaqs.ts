import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { getFaqs } from '../services/faqApi'
import type { FaqFilters } from '../types/faq.types'

export function useFaqs(filters: FaqFilters) {
  return useQuery({
    queryKey: ['faqs', filters],
    queryFn: ({ signal }) => getFaqs(filters, signal),
    placeholderData: keepPreviousData,
    staleTime: 30 * 1000,
    retry: false,
  })
}
