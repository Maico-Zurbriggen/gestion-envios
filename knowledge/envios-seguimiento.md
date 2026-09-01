# Registro de envíos y seguimiento público (HU03 / HU04)

Endpoints públicos, sin autenticación. Confirmados en Swagger (`/docs`) del backend.

## Registro de un envío (HU03)

- Endpoint: `POST /api/v1/envios`
- Acceso: público.
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

`terminos_aceptados` debe ser `true` o el backend rechaza la solicitud.

Respuesta exitosa (`201 Created`): devuelve el envío completo, con `token_seguimiento` (uno solo por envío, no por paquete) y cada paquete con su `numero_paquete` propio y estado inicial `"Pendiente"`. Este `numero_paquete` es el valor a codificar en el código de barras de la planilla imprimible (Escenario 4 de HU03); la generación del PDF/planilla es responsabilidad del frontend, el backend solo provee los datos.

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
- Un token corresponde a un único envío y devuelve **todos** los paquetes asociados a ese envío (Escenario 2 de HU04).

```json
{
  "status": "success",
  "data": {
    "token_seguimiento": "ENV-ADRZSPQ90K",
    "destino": "San Martin 100, Cordoba, Cordoba",
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

Token inexistente: `404` con el mismo esquema estándar de error:

```json
{ "status": "error", "code": "NOT_FOUND", "message": "No se encontró un envío asociado a ese código de seguimiento." }
```

### Pendiente para completar HU04 (fuera de este alcance de backend ya implementado)

- Escenarios 5 y 6 (distinción corta/larga distancia, mapa con recorrido y ubicación en tiempo real del repartidor) dependen de HU10/HU11 (recorridos y tracking del repartidor), todavía no implementadas. Por ahora `estado` solo refleja `"Pendiente"` desde el alta; no hay más transiciones de estado ni datos de recorrido.
- HU05 (envío del token por email y WhatsApp) no está implementada; el token solo se devuelve en la respuesta de `POST /api/v1/envios`.

## Identificadores

- `token_seguimiento`: formato `ENV-XXXXXXXXXX` (10 caracteres alfanuméricos en mayúsculas tras el prefijo), uno por envío.
- `numero_paquete`: formato `PAQ-XXXXXXXXXX`, uno por paquete, es el valor destinado al código de barras.

Ambos se generan con un PRNG criptográficamente seguro y se verifica su unicidad contra la base antes de persistir (`app/domain/rules/codigos_rules.py`).