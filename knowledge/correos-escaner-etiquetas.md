# Correos personalizables, escáner con el celular e impresión de etiquetas

## Correos a clientes

- Ruta: `/admin/correos`. Acceso: `ADMINISTRATIVO` y `SUPERADMIN`.
- Plantillas: `NUEVO_ENVIO_REMITENTE`, `NUEVO_ENVIO_DESTINATARIO` y `VISITA_FALLIDA`.
- Campos editables de cada plantilla: asunto, título, mensaje, texto del botón y nota final.
- Datos de la empresa, comunes a todos los correos: nombre, firma, teléfono, email, sitio web y aviso legal.
- **Variables:** se escriben entre llaves, por ejemplo `{nombre}` o `{token}`. Una variable que la plantilla no admite devuelve un error 400 que indica el campo.
- **Seguridad:** todo valor se escapa antes de entrar al HTML, así que los textos editados no pueden inyectar código.
- **Vista previa:** se arma con datos de ejemplo sobre los textos sin guardar y se muestra en un `iframe` con `sandbox` vacío.
- **Envío de prueba:** usa los textos en edición y antepone «[Prueba]» al asunto. Si el proveedor de correo lo rechaza, responde 400 con un mensaje genérico, sin el detalle interno del proveedor.
- **Sin personalizar:** si una plantilla no tiene textos guardados, o si leerlos falla, el envío usa los textos de fábrica. Un error de configuración nunca frena una notificación.
- **Persistencia:** tablas `plantillas_correo` y `configuracion_correo`, creadas por la migración `539e81c168e2`. Restablecer una plantilla borra su fila.

| Acción | Endpoint |
|---|---|
| Listar plantillas y datos de la empresa | `GET /api/v1/admin/correos/plantillas` |
| Guardar o restablecer | `PUT` / `DELETE /api/v1/admin/correos/plantillas/{clave}` |
| Datos de la empresa | `PUT /api/v1/admin/correos/configuracion` |
| Vista previa | `POST /api/v1/admin/correos/plantillas/{clave}/vista-previa` |
| Prueba | `POST /api/v1/admin/correos/plantillas/{clave}/prueba` |

## El celular como escáner

Basado en el escáner del administrador de stock de Tekron:

- **Motor de lectura:** `BarcodeDetector` nativo si existe; si no, ZXing (CODE_128 y QR), que se carga solo cuando hace falta.
- **Cámara:** se abre la trasera y se apaga siempre al cerrar el modal. La linterna aparece donde el navegador la ofrece.
- **Lectura:** el mismo código se ignora durante 2,5 s.
- **Modos:** único (retiro en sucursal) o continuo (recepción en terminal, con lista de los últimos leídos).
- **Repartidor:** «Escanear paquete» en recorridos de corta distancia en curso. Si el paquete corresponde, abre el registro de entrega o visita; si no, explica por qué.
- **Contexto seguro:** exige HTTPS o `localhost`. Para probar desde un celular en la red local: `HTTPS_DEV=true npm run dev`, que activa un certificado autofirmado y expone el servidor en la red.

## Impresión de etiquetas

Perfiles tomados de Soderia ERP, en `front/src/shared/printing/printerProfiles.ts`:

| Impresora | Tamaños |
|---|---|
| Zebra ZD220 y térmica genérica | 50×25, 40×30 mm |
| SATO CG408 / WS4 | 50×25, 40×30, 50×100, 100×50 mm |
| Brother QL-800 | 62×29, 29×90 mm |
| Etiqueta de envío | 100×150 mm (4×6") |
| Hoja común | A4 |

- **Diseños:** las etiquetas chicas llevan código de barras Code 128 y número; desde 50×100 llevan todos los datos del envío.
- **Cómo se imprime:** desde un `iframe` oculto con `@page { size; margin: 0 }`. La impresora se elige en el diálogo del navegador, y su driver debe tener el mismo tamaño de papel.
- **Configuración:** impresora, tamaño y copias (1 a 10). Se guarda por puesto con la clave `gestion-envios.impresion`.
- **Dónde está:** en el resultado del registro de envío («Imprimir etiquetas») y en la recepción en terminal («Reimprimir etiqueta»).
