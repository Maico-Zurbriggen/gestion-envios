export interface ApiTemplateTexts {
  asunto: string
  titulo: string
  mensaje: string
  texto_boton: string
  pie: string
}

export interface ApiTemplate extends ApiTemplateTexts {
  clave: string
  nombre: string
  descripcion: string
  variables: Array<{ nombre: string; descripcion: string }>
  personalizada: boolean
  updated_at: string | null
  de_fabrica: ApiTemplateTexts
}

export interface ApiEmailSettings {
  nombre_marca: string
  firma: string
  telefono_contacto: string
  email_contacto: string
  sitio_web: string
  mensaje_legal: string
  updated_at: string | null
}

export interface TemplateTexts {
  subject: string
  title: string
  message: string
  buttonText: string
  footer: string
}

export interface EmailTemplate extends TemplateTexts {
  key: string
  name: string
  description: string
  variables: Array<{ name: string; description: string }>
  customized: boolean
  updatedAt: string | null
  factory: TemplateTexts
}

export interface EmailSettings {
  brandName: string
  signature: string
  contactPhone: string
  contactEmail: string
  website: string
  legalNotice: string
  updatedAt: string | null
}

export interface EmailPreview {
  subject: string
  text: string
  html: string
}
