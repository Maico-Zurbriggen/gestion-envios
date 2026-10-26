# Trayectos por calles con Mapbox

## Alcance

El frontend de HU10 consulta [Mapbox Directions v5](https://docs.mapbox.com/api/navigation/directions/) con el perfil `mapbox/driving`. Leaflet conserva el mapa base de OpenStreetMap y dibuja la geometría GeoJSON que devuelve Mapbox, con la atribución de ambos proveedores.

El backend sigue siendo responsable de la asignación, persistencia y orden de los paquetes. Su trazado aproximado no se usa para dibujar las calles. Al guardar un orden diferente, agregar o quitar paradas se solicita la geometría del nuevo trayecto. Reasignar el repartidor o actualizar un detalle con las mismas coordenadas reutiliza la consulta en caché.

## Cálculo y presentación

- Se visita la sucursal inicial y las paradas con coordenadas en su orden guardado. En corta distancia se vuelve a la sucursal; en larga distancia se termina en la última parada.
- Directions acepta de 2 a 25 coordenadas por solicitud. Los recorridos mayores se dividen en bloques consecutivos de hasta 25, compartiendo la ubicación del límite. Las geometrías se dibujan separadas para no inventar una línea entre puntos ajustados de bloques diferentes. Se suman sus distancias y tiempos.
- Se solicitan `geometries=geojson`, `overview=full`, `continue_straight=false`, sin alternativas ni instrucciones de giro. Cada coordenada puede ajustarse a una carretera a hasta 1000 metros; si no hay un segmento transitable se informa el error.
- El detalle muestra la distancia por calles y el tiempo de conducción de Mapbox. Este tiempo no incluye atención o descarga en las paradas. Las tarjetas del listado identifican como aproximación la estimación de planificación del backend, que sí contempla atención en las paradas.
- Si faltan coordenadas, las métricas por calles se indican como parciales y se mantienen las advertencias de esos paquetes. Sin una sucursal válida o sin paradas ubicables no se solicita ni se inventa un trayecto.
- Ante errores, se conservan los marcadores y la lista accesible de paradas, con un mensaje y reintento manual cuando corresponde. No se sustituye el resultado por líneas rectas ni se muestran las estimaciones previas como si fueran distancias por carretera.

## Consultas remotas

`front/src/features/routes/services/mapboxRoutingApi.ts` contiene el acceso HTTP, los contratos están en `types/roadRoute.types.ts` y `useRoadRoute` integra TanStack Query. La clave usa las coordenadas y el perfil, sin incluir el token ni datos de contacto. La caché se considera vigente por 30 minutos, se elimina después de una hora sin observadores y no reintenta automáticamente ni consulta por recuperar foco o conexión. Cada solicitud tiene un límite de espera de 15 segundos y admite cancelación.

## Configuración local

Se necesita un token público de Mapbox en `VITE_GESTION_ENVIOS_MAPBOX_TOKEN`; también se acepta `VITE_MAPBOX_ACCESS_TOKEN` como configuración explícita del despliegue. No se guardan tokens en el código, documentos ni archivos versionados. El desarrollo local usa una variable del usuario de Windows, sin modificar archivos `.env`.

Para configurar una sesión de PowerShell antes de iniciar Vite desde `front/`:

```powershell
$env:VITE_GESTION_ENVIOS_MAPBOX_TOKEN = [Environment]::GetEnvironmentVariable('VITE_GESTION_ENVIOS_MAPBOX_TOKEN', 'User')
npm run dev
```

Después de configurar o cambiar la variable hay que reiniciar Vite. En otro equipo se debe configurar su propio token público. Como todo token `VITE_*`, está disponible para el navegador que realiza las consultas; no debe usarse un token secreto de servidor.

Referencias: [parámetros y límites de Directions](https://docs.mapbox.com/api/navigation/directions/), [tokens públicos](https://docs.mapbox.com/accounts/guides/tokens/), [atribución](https://docs.mapbox.com/help/dive-deeper/attribution/).
