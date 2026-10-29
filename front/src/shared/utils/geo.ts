/** Coordenadas válidas para dibujar en el mapa. */
export function isMapPoint(latitude: number | null | undefined, longitude: number | null | undefined): boolean {
  return latitude != null && longitude != null && Number.isFinite(latitude) && Number.isFinite(longitude)
    && latitude >= -90 && latitude <= 90 && longitude >= -180 && longitude <= 180
}
