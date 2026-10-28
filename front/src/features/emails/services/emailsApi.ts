import { operationalRequest } from '../../../shared/services/operationalApi'
import type {
  ApiEmailSettings,
  ApiTemplate,
  ApiTemplateTexts,
  EmailPreview,
  EmailSettings,
  EmailTemplate,
  TemplateTexts,
} from '../types/email.types'

const BASE = '/admin/correos'
const NOT_FOUND = { notFound: 'Esa plantilla de correo no existe.' }

function mapTexts(texts: ApiTemplateTexts): TemplateTexts {
  return {
    subject: texts.asunto,
    title: texts.titulo,
    message: texts.mensaje,
    buttonText: texts.texto_boton,
    footer: texts.pie,
  }
}

function toApiTexts(texts: Partial<TemplateTexts>): Partial<ApiTemplateTexts> {
  const body: Partial<ApiTemplateTexts> = {}
  if (texts.subject !== undefined) body.asunto = texts.subject
  if (texts.title !== undefined) body.titulo = texts.title
  if (texts.message !== undefined) body.mensaje = texts.message
  if (texts.buttonText !== undefined) body.texto_boton = texts.buttonText
  if (texts.footer !== undefined) body.pie = texts.footer
  return body
}

function mapTemplate(template: ApiTemplate): EmailTemplate {
  return {
    ...mapTexts(template),
    key: template.clave,
    name: template.nombre,
    description: template.descripcion,
    variables: template.variables.map((variable) => ({ name: variable.nombre, description: variable.descripcion })),
    customized: template.personalizada,
    updatedAt: template.updated_at,
    factory: mapTexts(template.de_fabrica),
  }
}

function mapSettings(settings: ApiEmailSettings): EmailSettings {
  return {
    brandName: settings.nombre_marca,
    signature: settings.firma,
    contactPhone: settings.telefono_contacto,
    contactEmail: settings.email_contacto,
    website: settings.sitio_web,
    legalNotice: settings.mensaje_legal,
    updatedAt: settings.updated_at,
  }
}

export async function getEmailTemplates(token: string) {
  const { data } = await operationalRequest<{ data: { plantillas: ApiTemplate[]; configuracion: ApiEmailSettings } }>(
    `${BASE}/plantillas`, token,
  )
  return { templates: data.plantillas.map(mapTemplate), settings: mapSettings(data.configuracion) }
}

export async function saveEmailTemplate(key: string, texts: TemplateTexts, token: string) {
  const { data } = await operationalRequest<{ data: ApiTemplate }>(
    `${BASE}/plantillas/${key}`, token, { method: 'PUT', body: JSON.stringify(toApiTexts(texts)) }, NOT_FOUND,
  )
  return mapTemplate(data)
}

export async function resetEmailTemplate(key: string, token: string) {
  const { data } = await operationalRequest<{ data: ApiTemplate }>(`${BASE}/plantillas/${key}`, token, { method: 'DELETE' }, NOT_FOUND)
  return mapTemplate(data)
}

export async function saveEmailSettings(settings: Omit<EmailSettings, 'updatedAt'>, token: string) {
  const { data } = await operationalRequest<{ data: ApiEmailSettings }>(`${BASE}/configuracion`, token, {
    method: 'PUT',
    body: JSON.stringify({
      nombre_marca: settings.brandName,
      firma: settings.signature,
      telefono_contacto: settings.contactPhone,
      email_contacto: settings.contactEmail,
      sitio_web: settings.website,
      mensaje_legal: settings.legalNotice,
    }),
  })
  return mapSettings(data)
}

export async function previewEmailTemplate(key: string, texts: TemplateTexts, token: string, signal?: AbortSignal): Promise<EmailPreview> {
  const { data } = await operationalRequest<{ data: { asunto: string; texto: string; html: string } }>(
    `${BASE}/plantillas/${key}/vista-previa`, token, { method: 'POST', body: JSON.stringify(toApiTexts(texts)), signal }, NOT_FOUND,
  )
  return { subject: data.asunto, text: data.texto, html: data.html }
}

export async function sendTestEmail(key: string, texts: TemplateTexts, email: string, token: string) {
  const { data } = await operationalRequest<{ data: { enviado: boolean; destino: string } }>(
    `${BASE}/plantillas/${key}/prueba`, token, { method: 'POST', body: JSON.stringify({ ...toApiTexts(texts), email }) }, NOT_FOUND,
  )
  return { sent: data.enviado, to: data.destino }
}
