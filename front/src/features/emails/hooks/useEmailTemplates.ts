import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAppSelector } from '../../../app/store'
import { selectAuthToken } from '../../auth/redux/authSlice'
import {
  getEmailTemplates,
  previewEmailTemplate,
  resetEmailTemplate,
  saveEmailSettings,
  saveEmailTemplate,
  sendTestEmail,
} from '../services/emailsApi'
import type { EmailSettings, TemplateTexts } from '../types/email.types'

const TEMPLATES_KEY = ['admin', 'email-templates'] as const

function useRequiredToken() {
  const token = useAppSelector(selectAuthToken)
  return () => {
    if (!token) throw new Error('La sesión venció. Volvé a iniciar sesión.')
    return token
  }
}

export function useEmailTemplates() {
  const token = useAppSelector(selectAuthToken)
  return useQuery({
    queryKey: TEMPLATES_KEY,
    queryFn: () => getEmailTemplates(token ?? ''),
    enabled: Boolean(token),
  })
}

/**
 * Vista previa con datos de ejemplo de los textos que se están editando
 * (sin guardar). El llamador le pasa los textos ya demorados para no pedir
 * una por cada tecla.
 */
export function useEmailPreview(key: string | null, texts: TemplateTexts | null) {
  const token = useAppSelector(selectAuthToken)
  return useQuery({
    queryKey: [...TEMPLATES_KEY, 'preview', key, texts],
    queryFn: ({ signal }) => previewEmailTemplate(key ?? '', texts as TemplateTexts, token ?? '', signal),
    enabled: Boolean(token && key && texts),
    placeholderData: keepPreviousData,
    retry: false,
    staleTime: 60_000,
  })
}

export function useEmailTemplateMutations() {
  const requireToken = useRequiredToken()
  const queryClient = useQueryClient()
  const invalidate = () => queryClient.invalidateQueries({ queryKey: TEMPLATES_KEY })

  return {
    save: useMutation({
      mutationFn: ({ key, texts }: { key: string; texts: TemplateTexts }) => saveEmailTemplate(key, texts, requireToken()),
      onSuccess: invalidate,
    }),
    reset: useMutation({
      mutationFn: (key: string) => resetEmailTemplate(key, requireToken()),
      onSuccess: invalidate,
    }),
    saveSettings: useMutation({
      mutationFn: (settings: Omit<EmailSettings, 'updatedAt'>) => saveEmailSettings(settings, requireToken()),
      onSuccess: invalidate,
    }),
    sendTest: useMutation({
      mutationFn: ({ key, texts, email }: { key: string; texts: TemplateTexts; email: string }) =>
        sendTestEmail(key, texts, email, requireToken()),
    }),
  }
}
