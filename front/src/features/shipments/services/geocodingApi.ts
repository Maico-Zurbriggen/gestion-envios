const nominatimUrl = 'https://nominatim.openstreetmap.org/search'
const resultCache = new Map<string, NominatimResult | null>()

interface NominatimResult {
  lat: string
  lon: string
  display_name: string
}

export interface GeocodingInput {
  street: string
  streetNumber: string
  city: string
  province: string
}

export interface GeocodingResult {
  latitude: number
  longitude: number
  label: string
  precision: 'address' | 'city'
}

async function searchLocation(query: string): Promise<NominatimResult | null> {
  const cacheKey = query.trim().toLocaleLowerCase('es-AR')
  if (resultCache.has(cacheKey)) return resultCache.get(cacheKey) ?? null

  const params = new URLSearchParams({
    q: query,
    format: 'jsonv2',
    limit: '1',
    countrycodes: 'ar',
  })

  let response: Response

  try {
    response = await fetch(`${nominatimUrl}?${params.toString()}`, {
      headers: {
        Accept: 'application/json',
        'Accept-Language': 'es-AR,es;q=0.9',
      },
    })
  } catch {
    throw new Error('No pudimos conectarnos con el servicio de mapas.')
  }

  if (!response.ok) {
    if (response.status === 429) {
      throw new Error(
        'El servicio de mapas está recibiendo muchas consultas. Esperá unos segundos.',
      )
    }

    throw new Error('No pudimos consultar la ubicación en este momento.')
  }

  const payload = (await response.json()) as NominatimResult[]
  const result = Array.isArray(payload) && payload.length ? payload[0] : null
  resultCache.set(cacheKey, result)
  return result
}

function waitForNextRequest() {
  return new Promise<void>((resolve) => {
    window.setTimeout(resolve, 1100)
  })
}

export async function geocodeDestination(
  input: GeocodingInput,
): Promise<GeocodingResult> {
  const fullAddress = [
    `${input.streetNumber} ${input.street}`,
    input.city,
    input.province,
    'Argentina',
  ].join(', ')

  const addressResult = await searchLocation(fullAddress)
  if (addressResult) {
    return {
      latitude: Number(addressResult.lat),
      longitude: Number(addressResult.lon),
      label: addressResult.display_name,
      precision: 'address',
    }
  }

  await waitForNextRequest()
  const cityResult = await searchLocation(
    `${input.city}, ${input.province}, Argentina`,
  )

  if (!cityResult) {
    throw new Error(
      'No encontramos la dirección ni la ciudad. Revisá cómo están escritas.',
    )
  }

  return {
    latitude: Number(cityResult.lat),
    longitude: Number(cityResult.lon),
    label: cityResult.display_name,
    precision: 'city',
  }
}
