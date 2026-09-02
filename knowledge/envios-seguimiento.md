# Registro de envíos y seguimiento público (HU03 / HU04)

Endpoints públicos, sin autenticación. Confirmados en Swagger (`/docs`) del backend.

## Registro de un envío (HU03)

- Endpoint: `POST /api/v1/envios`
- Acceso: público.
- Ruta del frontend: `/envios/nuevo`, disponible tanto sin sesión como desde el panel autenticado.
- Un envío tiene un remitente, un destinatario y uno o más paquetes (`paquetes: []`, mínimo 1).

Cuerpo de la solicitud:

```json
{
  "remitente_nombre": "Juan Perez",
  "remitente_documento": "30111222",
  "remitente_telefono": "3564111222",
  "remitente_email": "juan@example.com",
  "destinatario_nombre": "Maria Lopez",
  "destinatario_telefono": "3564333444",
  "destinatario_email": "maria@example.com",
  "tipo_entrega": "domicilio",
  "provincia_destino": "Cordoba",
  "ciudad_destino": "Cordoba",
  "direccion_destino": "San Martin 100",
  "latitud_destino": -31.4167,
  "longitud_destino": -64.1833,
  "sucursal_destino_id": null,
  "terminos_aceptados": true,
  "paquetes": [
    { "descripcion": "Ropa", "peso_kg": 2, "largo_cm": 30, "ancho_cm": 20, "alto_cm": 10, "observaciones": null }
  ]
}
```

`tipo_entrega` es `"domicilio"` o `"sucursal"` y condiciona qué campos son obligatorios:

- `domicilio`: requiere `provincia_destino`, `ciudad_destino` y `direccion_destino`. `latitud_destino`/`longitud_destino` son opcionales (marcado en mapa, Escenario 3 de HU03); si no se marca un punto, alcanza con la dirección tipeada.
- `sucursal`: requiere `sucursal_destino_id` (ver `GET /api/v1/sucursales`).

En el frontend, el domicilio se solicita como provincia, ciudad, calle y altura; calle y altura se combinan en `direccion_destino`. Las coordenadas no se escriben en campos: se obtienen opcionalmente al marcar un punto en un mapa Leaflet con mosaicos de OpenStreetMap. La acción `Ubicar en el mapa` consulta Nominatim únicamente por decisión del usuario, primero con la dirección completa y, si no hay coincidencia, con ciudad y provincia. Las consultas se almacenan temporalmente en memoria y el fallback respeta un intervalo mayor a un segundo entre solicitudes. Para retiro en sucursal, antes de elegir se informa que su ubicación aparecerá en el mapa y, luego de seleccionar, se centra el mapa usando las coordenadas del catálogo.

`terminos_aceptados` debe ser `true` o el backend rechaza la solicitud.

Respuesta exitosa (`201 Created`): devuelve el envío completo, con `token_seguimiento` (uno solo por envío, no por paquete) y cada paquete con su `numero_paquete` propio y estado inicial `"Pendiente"`. Este `numero_paquete` es el valor a codificar en el código de barras de la planilla imprimible (Escenario 4 de HU03); la generación del PDF/planilla es responsabilidad del frontend, el backend solo provee los datos.

El frontend genera una etiqueta por paquete en formato imprimible A4. Cada etiqueta incorpora un código de barras Code 128 construido con `numero_paquete`, además de los datos de remitente, destinatario, destino, peso y medidas. Se puede imprimir desde el navegador o descargar directamente un PDF generado localmente con una página por bulto. El `token_seguimiento` se muestra y puede copiarse, pero no reemplaza al número de paquete utilizado para el escaneo en sucursal.

```json
{
  "status": "success",
  "message": "Envío registrado correctamente.",
  "data": {
    "id": "6af09a10-...",
    "token_seguimiento": "ENV-ADRZSPQ90K",
    "remitente_nombre": "...",
    "...": "resto de remitente/destinatario",
    "tipo_entrega": "domicilio",
    "sucursal_destino": null,
    "paquetes": [
      { "id": "d476fa8c-...", "numero_paquete": "PAQ-ZPC5LB48JJ", "descripcion": "Ropa", "peso_kg": 2.0, "largo_cm": 30.0, "ancho_cm": 20.0, "alto_cm": 10.0, "observaciones": null, "estado": "Pendiente" }
    ],
    "created_at": "2026-09-01T12:27:21"
  }
}
```

Si `tipo_entrega` es `"sucursal"`, `sucursal_destino` viene poblado con los datos de la sucursal (ver estructura en la sección siguiente) y los campos de domicilio quedan en `null`.

### Restricciones de paquete (Escenario 2 de HU03)

Por cada paquete se valida, en el dominio (`app/domain/rules/paquete_rules.py`):

- Peso: mayor a 0 y hasta 25 kg.
- Cada dimensión (`largo_cm`, `ancho_cm`, `alto_cm`): mayor a 0 y hasta 150 cm.
- Suma de las tres dimensiones: hasta 250 cm.

Si algún paquete incumple, la respuesta es `400` con `code: "VALIDATION_ERROR"` y un array `errors` donde cada `field` está prefijado con el índice del paquete, por ejemplo `paquetes[0].peso_kg`. Ver el esquema general de errores en [Autenticación](./authentication.md) — es el mismo formato en todo el backend.

## Listado de sucursales (soporte de HU03 y HU09)

- Endpoint: `GET /api/v1/sucursales`
- Acceso: público.
- Alimenta el selector de sucursal cuando `tipo_entrega = "sucursal"`, y la futura vista de HU09 (retiro en sucursal).

```json
{
  "status": "success",
  "data": [
    { "id": 1, "nombre": "Sucursal Córdoba Centro", "provincia": "Córdoba", "ciudad": "Córdoba", "direccion": "Av. Colón 1234", "latitud": -31.4167, "longitud": -64.1833 }
  ]
}
```

Las 6 sucursales base se siembran automáticamente al iniciar el backend (`app/infrastructure/db/seed.py`); no requieren alta manual en desarrollo.

## Seguimiento público por token (HU04)

- Endpoint: `GET /api/v1/seguimiento/{token}`
- Acceso: público.
- Ruta del frontend: `/seguimiento`; acepta opcionalmente `?token=ENV-...` para compartir una consulta directa.
- Un token corresponde a un único envío y devuelve **todos** los paquetes asociados a ese envío (Escenario 2 de HU04).

```json
{
  "status": "success",
  "data": {
    "token_seguimiento": "ENV-ADRZSPQ90K",
    "destino": "San Martin 100, Cordoba, Cordoba",
    "latitud_destino": -31.4167,
    "longitud_destino": -64.1833,
    "paquetes": [
      {
        "numero_paquete": "PAQ-ZPC5LB48JJ",
        "estado": "Pendiente",
        "descripcion": "Ropa",
        "observaciones": null,
        "fecha_registro": "2026-09-01T12:27:21",
        "ultima_actualizacion": "2026-09-01T12:27:21"
      }
    ]
  }
}
```

`destino` ya viene armado como un único string legible por el backend (dirección completa si es a domicilio, o nombre y dirección de la sucursal si es retiro), para que la vista pública no tenga que componerlo.

`latitud_destino`/`longitud_destino` **(campo nuevo, agregado 2026-09-02)** son la ubicación fija de entrega: las coordenadas fijas de la sucursal si `tipo_entrega = "sucursal"`, o las que el remitente marcó en el mapa al registrar el envío si fue a domicilio. En este último caso **pueden venir en `null`** — el remitente pudo no haber marcado ningún punto, el domicilio tipeado igual es válido. No es la ubicación en tiempo real del repartidor (eso sigue dependiendo de HU10/HU11, ver más abajo).

La vista presenta cada paquete por separado, con su estado real, contenido, observaciones, fechas y un recorrido operativo de cuatro etapas: registrado, recibido en sucursal, en viaje y entregado. Las etapas futuras son solamente una representación visual inactiva; el estado textual devuelto por el backend es la fuente de verdad.

Token inexistente: `404` con el mismo esquema estándar de error:

```json
{ "status": "error", "code": "NOT_FOUND", "message": "No se encontró un envío asociado a ese código de seguimiento." }
```

### Pendiente para completar HU04

**Tarea de frontend disponible ahora — falta la "muestra en mapa" en `/seguimiento`:**

El backend ya expone `latitud_destino`/`longitud_destino` en `GET /api/v1/seguimiento/{token}` (ver arriba). Falta consumirlo en `TrackingPage.tsx`, que hoy solo muestra el cartel fijo "La ubicación en tiempo real se verá cuando el repartidor comience su recorrido" sin ningún mapa. Propuesta concreta, reutilizando lo que ya existe en el registro de envíos:

- Sumar `latitude`/`longitude` a `ShipmentTracking` (`tracking.types.ts`) y mapearlos en `trackingApi.ts` desde `latitud_destino`/`longitud_destino`.
- En `TrackingPage.tsx`, cuando haya coordenadas, renderizar `<ShipmentMap mode="location" latitude={...} longitude={...} accessibleName="Ubicación de destino" />` (el mismo componente de `features/shipments/components/ShipmentMap.tsx`, ya usado para mostrar la ubicación fija de una sucursal en `CreateShipmentPage.tsx`).
- Cuando no haya coordenadas (domicilio sin marcar en el mapa), usar el mismo patrón de placeholder que ya existe para sucursales sin coordenadas ("Ubicación no disponible…").
- Mantener el texto que aclara que el recorrido en tiempo real llega con HU10/HU11 — no se reemplaza, se complementa con el mapa de destino fijo.
- Como `ShipmentMap` se usaría desde dos features distintas (`shipments` y `tracking`), evaluar si conviene moverlo (junto con el CSS del mapa en sí: `.shipment-map`, `.shipment-map--picker`, `.shipment-map__point`) a un lugar compartido (`front/src/shared/components/`) en vez de importarlo cruzado entre features.

**Todavía no implementado (no depende de este backend):**

- Escenarios 5 y 6 completos (distinción corta/larga distancia, mapa con el recorrido y ubicación en tiempo real del repartidor) dependen de HU10/HU11 (generación de recorridos y tracking del repartidor), que no están implementadas ni en backend ni en frontend. Lo de arriba resuelve solo "dónde va el paquete" (destino fijo), no "dónde está el repartidor ahora".
- HU05 (envío del token por email y WhatsApp) no está implementada; el token solo se devuelve en la respuesta de `POST /api/v1/envios`.
- HU06 (lectura de código de barras al recibir el paquete en terminal) no está implementada: no existe endpoint de backend ni pantalla de frontend. Requiere definir primero rol autorizado (`VENDEDOR`), transición de estado esperada y si la lectura es manual o por cámara.

## Identificadores

- `token_seguimiento`: formato `ENV-XXXXXXXXXX` (10 caracteres alfanuméricos en mayúsculas tras el prefijo), uno por envío.
- `numero_paquete`: formato `PAQ-XXXXXXXXXX`, uno por paquete, es el valor destinado al código de barras.

Ambos se generan con un PRNG criptográficamente seguro y se verifica su unicidad contra la base antes de persistir (`app/domain/rules/codigos_rules.py`).
