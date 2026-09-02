# HU04 — Seguimiento público por token

> Yo como emisor o destinatario deseo consultar el seguimiento de uno o varios paquetes mediante un token, sin iniciar sesión, para conocer el estado del envío desde una vista pública común para ambas partes.

Ver también el contrato orientado a frontend en [`knowledge/envios-seguimiento.md`](../../../knowledge/envios-seguimiento.md).

## Endpoint

`GET /api/v1/seguimiento/{token}` — público, sin autenticación (router `app/api/v1/routers/seguimiento.py`).

## Diseño clave: el token identifica un envío, no un paquete

`token_seguimiento` es una columna de `EnvioModel`, no de `PaqueteModel` (ver [Modelo de datos](../01-arquitectura/modelo-de-datos.md)). Esto resuelve directamente el Escenario 2 de HU04 ("un mismo token asociado a más de un paquete"): `ServicioSeguimiento.obtener_seguimiento` busca un único `EnvioModel` por token (`RepositorioEnvios.obtener_por_token`, con `paquetes` cargados por `selectinload`) y devuelve la lista completa de sus paquetes en un solo response — no hay que consultar el token varias veces ni pasar un índice de paquete.

## Armado del campo `destino`

En vez de que el frontend tenga que decidir si mostrar dirección o sucursal, `ServicioSeguimiento` arma un único string legible según `tipo_entrega`:

```python
if envio.tipo_entrega == "domicilio":
    destino = f"{envio.direccion_destino}, {envio.ciudad_destino}, {envio.provincia_destino}"
else:
    destino = f"Sucursal {sucursal.nombre} - {sucursal.direccion}, {sucursal.ciudad}, {sucursal.provincia}"
```

Esto cubre tanto el Escenario 1 (mostrar domicilio) como el caso de retiro en sucursal, sin que la vista pública necesite lógica condicional adicional.

## Coordenadas del destino (`latitud_destino` / `longitud_destino`)

Además del string `destino`, la respuesta expone las coordenadas fijas del punto de entrega, para que el frontend pueda dibujar un mapa (Leaflet + OpenStreetMap, mismo componente ya usado en el registro de envíos) sin tener que geocodificar nada de nuevo:

- `tipo_entrega = "domicilio"` → `envio.latitud_destino` / `envio.longitud_destino`, las que el remitente marcó en el mapa al registrar el envío (HU03 Escenario 3). **Pueden ser `None`** si no marcó ningún punto — el domicilio tipeado sigue siendo válido sin coordenadas.
- `tipo_entrega = "sucursal"` → las coordenadas fijas de `sucursal_destino` (siempre presentes, vienen del catálogo sembrado).

Importante: esto es la ubicación **fija** de destino, no la ubicación en tiempo real del repartidor — ver la sección de Escenarios 5 y 6 más abajo, que sigue sin implementarse.

## Qué información se expone (y qué no)

La respuesta incluye, por paquete: `numero_paquete`, `estado`, `descripcion`, `observaciones`, `fecha_registro` (`created_at`) y `ultima_actualizacion` (`updated_at`) — exactamente lo que pide el Escenario 1 ("número de paquete, estado, fecha de registro, última actualización, domicilio y observaciones").

**Deliberadamente no se exponen** documento, teléfono ni email de remitente/destinatario en esta vista pública — son datos de contacto sensibles que no forman parte del criterio de aceptación de HU04, y exponerlos en un endpoint sin autenticación (accesible por cualquiera que adivine o intercepte un token) sería un riesgo innecesario. Esto está verificado explícitamente en `tests/integration/test_seguimiento.py::test_hu04_escenario_1_consulta_publica_con_token_valido`.

## Escenario 3 — Token inexistente

`RepositorioEnvios.obtener_por_token` devuelve `None` si no hay coincidencia; `ServicioSeguimiento` lo traduce a `NotFoundException` → `404 NOT_FOUND` con un mensaje descriptivo y sin ninguna clave `data` en la respuesta (se verifica en el test correspondiente).

## Escenario 4 — Misma vista para ambas partes

No hay ningún concepto de "rol" ni "quién soy" en este endpoint: quien tenga el token ve exactamente la misma respuesta, sea remitente o destinatario. No hay branching de lógica por identidad porque el endpoint no recibe ni necesita esa información.

## Escenarios 5 y 6 — Corta/larga distancia, mapa de recorrido

**No implementados todavía.** Dependen de funcionalidad de historias posteriores del backlog:

- HU10 (generación de recorridos) y HU11 (tracking del repartidor en el mapa) son las que producirían los datos de "recorrido" y "ubicación en tiempo real" que estos escenarios necesitan mostrar. `latitud_destino`/`longitud_destino` (ver sección anterior) alcanzan para mostrar **dónde va** el paquete, pero no reemplazan el recorrido ni la posición del repartidor.
- Por ahora, `estado` de un paquete solo puede valer `"Pendiente"` (el único valor que asigna el registro de HU03) — no hay transiciones de estado que reflejen "en sucursal de origen", "en camino", etc. Cuando se implementen esas historias, este documento y `contracts/seguimiento.py` deben actualizarse para incluir los datos de recorrido/ubicación.

## Endpoint relacionado: catálogo de sucursales

`GET /api/v1/sucursales` (router `app/api/v1/routers/sucursales.py`) es público y sin autenticación. Alimenta tanto el selector de "retiro en sucursal" del formulario de HU03 como la futura vista de HU09. Devuelve el listado completo sembrado en `infrastructure/db/seed.py:sembrar_sucursales`; no tiene paginación ni filtros porque el catálogo es chico y fijo en esta etapa.

## Tests relevantes

`tests/integration/test_seguimiento.py` (los 5 escenarios de HU04, incluyendo el que confirma qué campos NO se exponen y los que verifican las coordenadas de destino en sus tres casos: domicilio con mapa marcado, domicilio sin marcar y sucursal) y `tests/integration/test_sucursales.py`.