import { useSyncExternalStore } from 'react'
import { DEFAULT_PRINT_SETTINGS, normalizePrintSettings, type PrintSettings } from './printerProfiles'

/**
 * La impresora depende del puesto, no de la persona: se guarda en este
 * navegador como comodidad local y nunca viaja al servidor.
 */
const PRINT_SETTINGS_STORAGE_KEY = 'gestion-envios.impresion'

const listeners = new Set<() => void>()
let cachedRaw: string | null | undefined
let cachedSettings: PrintSettings = DEFAULT_PRINT_SETTINGS
// Respaldo en memoria cuando el navegador bloquea el almacenamiento local.
let memoryRaw: string | null = null

function readRaw(): string | null {
  try {
    return localStorage.getItem(PRINT_SETTINGS_STORAGE_KEY)
  } catch {
    return memoryRaw
  }
}

function parseSettings(raw: string | null): PrintSettings {
  if (!raw) return DEFAULT_PRINT_SETTINGS
  try {
    return normalizePrintSettings(JSON.parse(raw))
  } catch {
    return DEFAULT_PRINT_SETTINGS
  }
}

function getSnapshot(): PrintSettings {
  const raw = readRaw()
  if (raw !== cachedRaw) {
    cachedRaw = raw
    cachedSettings = parseSettings(raw)
  }
  return cachedSettings
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  const onStorage = (event: StorageEvent) => {
    if (event.key === null || event.key === PRINT_SETTINGS_STORAGE_KEY) listener()
  }
  window.addEventListener('storage', onStorage)
  return () => {
    listeners.delete(listener)
    window.removeEventListener('storage', onStorage)
  }
}

function savePrintSettings(settings: PrintSettings) {
  const raw = JSON.stringify(normalizePrintSettings(settings))
  memoryRaw = raw
  try {
    localStorage.setItem(PRINT_SETTINGS_STORAGE_KEY, raw)
  } catch {
    // Sin almacenamiento disponible la configuración dura hasta recargar.
  }
  listeners.forEach((listener) => listener())
}

export function usePrintSettings() {
  const settings = useSyncExternalStore(subscribe, getSnapshot, () => DEFAULT_PRINT_SETTINGS)
  return [settings, savePrintSettings] as const
}
