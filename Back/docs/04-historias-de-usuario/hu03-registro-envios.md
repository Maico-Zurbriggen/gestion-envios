# HU03 — Registro de envíos

> Yo como persona que envía un paquete deseo registrar los datos del envío y generar la planilla que se coloca en el paquete, para dejar el envío precargado antes de llevarlo a la central y evitar volver a cargar la información.

Ver también el contrato orientado a frontend en [`knowledge/envios-seguimiento.md`](../../../knowledge/envios-seguimiento.md); este documento se enfoca en la lógica interna.

## Endpoint

`POST /api/v1/envios` — público, sin autenticación (router `app/api/v1/routers/envios.py`).

## Modelo del request (`contracts/envios.py:CrearEnvioRequest`)

Un envío agrupa remitente, destinatario, destino y una lista de paquetes (`paquetes: list[PaqueteRequest]`, mínimo 1 — un mismo viaje puede llevar varias cajas del mismo remitente al mismo destinatario, compartiendo un solo token).

### Validación de destino: `tipo_entrega`

El campo `tipo_entrega` (`"domicilio"` o `"sucursal"`) es lo único que decide qué otros campos son obligatorios, resuelto en `CrearEnvioRequest.validar_terminos_y_destino` (un `model_validator` de Pydantic, no una constraint de base de datos):

- `"domicilio"` → obligatorios `provincia_destino`, `ciudad_destino`, `direccion_destino`. `latitud_destino`/`longitud_destino` son opcionales: cubren el Escenario 3 (marcado en mapa), pero si el usuario tipea la dirección a mano sin marcar el mapa, el registro igual es válido.
- `"sucursal"` → obligatorio `sucursal_destino_id`, que debe existir en la tabla `sucursales` (`ServicioEnvios.crear_envio` lo verifica contra `RepositorioSucursales.obtener_por_id`; si no existe, `400 VALIDATION_ERROR` con `field: "sucursal_destino_id"`).

También se exige `terminos_aceptados: true` en el mismo validador — si viene `false`, el registro se rechaza aunque el resto de los datos sea válido (Escenario 1, "se aceptan los términos y condiciones").

### Validación de paquetes (Escenario 2)

Antes de tocar la base de datos, `ServicioEnvios.crear_envio` valida cada paquete de la lista contra `domain/rules/paquete_rules.py:validar_paquete`:

| Restricción | Límite |
|---|---|
| Peso | mayor a 0 kg, hasta 25 kg |
| Cada dimensión (largo, ancho, alto) | mayor a 0 cm, hasta 150 cm |
| Suma largo + ancho + alto | hasta 250 cm |

Es una función pura de dominio: no lanza excepciones, devuelve una lista de `{"field": ..., "message": ...}` (vacía si no hay errores). El servicio junta los errores de **todos** los paquetes antes de responder, prefijando el campo con el índice del paquete en la lista (`paquetes[0].peso_kg`, `paquetes[1].dimensiones`, etc.), para que el frontend pueda marcar el paquete exacto que falla en un formulario con varios paquetes cargados.

## Generación de identificadores (Escenario 1)

`domain/rules/codigos_rules.py` genera dos tipos de código, ambos con el mismo esquema (prefijo + 10 caracteres alfanuméricos en mayúscula, generados con `secrets` — PRNG criptográfico):

- `token_seguimiento` (`ENV-XXXXXXXXXX`): uno por envío, compartido por todos sus paquetes.
- `numero_paquete` (`PAQ-XXXXXXXXXX`): uno por paquete, pensado para codificarse en el código de barras de la planilla.

`ServicioEnvios._generar_token_unico` y `_generar_numero_paquete_unico` reintentan hasta 5 veces si el candidato ya existe en base (colisión extremadamente improbable, pero se verifica igual); si agotan los intentos, devuelven `500 INTERNAL_ERROR` en vez de arriesgarse a persistir un duplicado.

## Qué devuelve el registro exitoso (Escenario 1 y 4)

La respuesta (`201 Created`) incluye el envío completo con sus paquetes, cada uno con su `numero_paquete` y estado inicial `"Pendiente"`. La generación de la **planilla imprimible en sí** (PDF con el código de barras, Escenario 4) es responsabilidad del frontend a partir de estos datos — el backend no genera PDFs ni imágenes de código de barras, solo provee el `numero_paquete` a codificar.

## Qué queda fuera de esta implementación

- El Escenario 5 (consulta de términos y condiciones / restricciones y contenidos prohibidos) es contenido estático que se espera resuelva el frontend; el backend no expone un endpoint de "términos".
- El listado de sucursales para el selector de retiro vive en un endpoint separado, `GET /api/v1/sucursales` (documentado junto con HU04, ya que ambas HU lo comparten).

## Tests relevantes

`tests/integration/test_envios_registro.py` — registro a domicilio, registro a sucursal con múltiples paquetes, rechazo por términos no aceptados, rechazo por sucursal inválida, rechazo por domicilio incompleto, y los tres casos de límites de paquete (peso, dimensión individual, suma de dimensiones). `tests/unit/test_paquete_rules.py` y `tests/unit/test_codigos_rules.py` cubren las reglas de dominio en aislamiento.