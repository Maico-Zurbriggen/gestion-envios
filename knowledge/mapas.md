# Mapas, recorridos por calles y ubicación de direcciones

El mismo esquema que Rumbo (Aviso Entrega Completa). Todo es gratis y sin claves.

| Servicio | Para qué | Dónde |
|---|---|---|
| **OpenFreeMap** | Imágenes del mapa (estilo `liberty` en claro y `dark` en oscuro). | Frontend, `shared/components/MapView.tsx` con MapLibre (`react-map-gl`). Se puede servir un estilo propio con `VITE_MAP_STYLE_URL` y `VITE_MAP_STYLE_DARK_URL`. |
| **OSRM** | Recorrido por calles y rutas, distancia y tiempo de manejo, y la matriz de tiempos para ordenar las paradas. | Backend, `infrastructure/mapas/rutas.py`, con `OSRM_URL`. |
| **Georef** (datos.gob.ar) | Ubicar en el mapa cada dirección de entrega. | Backend, `infrastructure/mapas/ubicacion.py`. |
| **Nominatim** (OpenStreetMap) | Respaldo de Georef: una consulta por segundo. | Backend, mismo archivo. |

## Recorridos por calles

- **Sin diagonales.** El mapa dibuja solo el recorrido real de OSRM, con borde blanco y el color de la marca. Si OSRM no responde, se ven las paradas numeradas en orden y un aviso, nunca líneas rectas.
- **El orden más rápido.** El armado automático y «Optimizar» piden a OSRM la matriz de tiempos reales de manejo entre todas las paradas, que respeta sentidos de circulación, avenidas y rutas. Sobre esa matriz aplican vecino más cercano y mejora 2-opt (`ServicioRecorridos._ordenar`). Sin OSRM, usan la distancia estimada.
- **Dónde está «Optimizar recorrido».** En cada tarjeta del día, en el armado del recorrido y en la app del repartidor; antes de salir ordena todo y en reparto, lo que falta desde la posición del vehículo. El recorrido nuevo se crea ya optimizado («Optimizar recorrido al crear», marcado por defecto). El botón siempre se ve mientras el recorrido no terminó; con una sola parada queda deshabilitado y lo explica.
- **Distancia y tiempo.** Salen del recorrido por calles más los minutos de atención en cada parada (5 a domicilio, 15 en una sucursal). El tiempo de OSRM se multiplica por `RUTAS_FACTOR_TRAFICO` (1,2).
- `POST /api/v1/mapa/trayecto` (con sesión) devuelve la geometría `[longitud, latitud]`, la distancia y el tiempo de un recorrido. Lo usan el panel de recorridos y la app del repartidor.

### OSRM propio (producción)

Por defecto `OSRM_URL` apunta al servidor público de demostración de OSRM: alcanza para probar, pero solo admite uso liviano (el backend respeta una consulta por segundo). En producción se usa el propio, igual que Rumbo:

```bash
docker compose -f deploy/osrm/docker-compose.yml --profile preparar run --rm osrm-prepare   # una vez y cada mes
docker compose -f deploy/osrm/docker-compose.yml up -d osrm
# .env del backend:  OSRM_URL=http://localhost:5000
```

Usa unos 3 GB de memoria. El mapa de Argentina se baja de Geofabrik (o del espejo de openstreetmap.fr).

## Ubicar direcciones

`GET /api/v1/mapa/ubicar?calle=&altura=&ciudad=&provincia=` es pública (la usa el registro de envíos). Busca en este orden:

1. **Georef** con calle y altura. Valida que la calle sea de esa localidad, porque Georef no tiene todas las calles y puede devolver una homónima de otra ciudad.
2. **Nominatim**, si Georef no la encuentra.
3. **El centro de la ciudad** (Georef), marcado como ubicación aproximada para que la persona ajuste el punto en el mapa.

Las respuestas con altura o calle quedan en memoria para no repetir consultas.
