/** Ubicación de direcciones: el backend consulta Georef (Estado Argentino) y, si no la encuentra, OpenStreetMap. */
interface GeocodingInput {
  street: string
  streetNumber: string
  city: string
  province: string
}

interface GeocodingResult {
  latitude: number
  longitude: number
  label: string
  precision: 'address' | 'city'
}

interface ApiLocation {
  data?: { latitud: number; longitud: number; texto: string; precision: 'direccion' | 'calle' | 'ciudad' }
  message?: string
}

const cache = new Map<string, GeocodingResult>()

export async function geocodeDestination(input: GeocodingInput): Promise<GeocodingResult> {
  const apiUrl = import.meta.env.VITE_API_URL?.replace(/\/+$/, '')
  if (!apiUrl) throw new Error('No se configuró la URL de la API.')
  const params = new URLSearchParams({ calle: input.street.trim(), altura: input.streetNumber.trim(), ciudad: input.city.trim(), provincia: input.province.trim() })
  const key = params.toString().toLocaleLowerCase('es-AR')
  const cached = cache.get(key)
  if (cached) return cached

  let response: Response
  try {
    response = await fetch(`${apiUrl}/mapa/ubicar?${params}`, { headers: { Accept: 'application/json' } })
  } catch {
    throw new Error('No pudimos conectarnos con el servicio de mapas.')
  }
  const payload = (await response.json().catch(() => null)) as ApiLocation | null
  if (response.status === 404) throw new Error('No encontramos la dirección ni la ciudad. Revisá cómo están escritas.')
  if (!response.ok || !payload?.data) throw new Error('No pudimos consultar la ubicación en este momento.')

  const result: GeocodingResult = {
    latitude: payload.data.latitud,
    longitude: payload.data.longitud,
    label: payload.data.texto,
    precision: payload.data.precision === 'ciudad' ? 'city' : 'address',
  }
  cache.set(key, result)
  return result
}
