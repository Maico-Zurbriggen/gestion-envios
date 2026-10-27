# Notificaciones por email (Gmail) y WhatsApp

HU05 envía el código de seguimiento por **email y WhatsApp** al remitente y al destinatario cuando se registra un envío. La visita fallida de HU12 avisa al destinatario por los mismos dos canales. Cada intento queda en `notificaciones_envio` y el personal lo ve (y lo reenvía) desde **Recepción en terminal → Avisos al cliente**.

Por defecto los dos canales usan proveedores **mock**: no envían nada, solo registran el mensaje en el log. Para enviar de verdad hay que completar `Back/.env` como se explica abajo. Ningún valor de esta guía va al repositorio.

## Email con Gmail

1. En la cuenta de Google que va a enviar los correos, activar la **verificación en dos pasos** (Cuenta de Google → Seguridad).
2. Crear una **contraseña de aplicación** en <https://myaccount.google.com/apppasswords> (nombre sugerido: "Gestión de envíos"). Google muestra 16 caracteres: copiarlos sin espacios. La contraseña normal de la cuenta **no funciona** con SMTP.
3. En `Back/.env`:

   ```dotenv
   EMAIL_PROVIDER=gmail
   SMTP_USER=tu.cuenta@gmail.com
   SMTP_PASSWORD=abcdabcdabcdabcd
   SMTP_FROM_NAME="Gestión de Envíos"
   FRONTEND_BASE_URL=http://localhost:5173
   ```

   `EMAIL_PROVIDER=gmail` completa `smtp.gmail.com:587` con STARTTLS. Para el puerto 465 (SSL) agregar `SMTP_PORT=465`. `SMTP_FROM_EMAIL` vacío usa `SMTP_USER`, que es lo que Gmail exige: si el remitente no coincide con la cuenta autenticada, Gmail lo reescribe.
4. `FRONTEND_BASE_URL` es la URL pública del frontend: es la que va en el enlace del mensaje. En una demo con la API en otra máquina, poner la URL real y no `localhost`.

Otros proveedores SMTP (Outlook, Mailtrap, un servidor propio) usan `EMAIL_PROVIDER=smtp` con `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` y `SMTP_USE_TLS`.

**Límites:** una cuenta gratuita de Gmail admite unos cientos de envíos por día. Si Google rechaza las credenciales, el aviso queda `FALLIDO` con el código SMTP y la indicación de usar una contraseña de aplicación.

## WhatsApp

WhatsApp solo deja que una empresa **inicie** una conversación con una **plantilla aprobada**. El texto libre se entrega únicamente si la persona escribió al número de la empresa en las últimas 24 horas (o, en Twilio, si se unió al sandbox). Hay dos proveedores implementados; elegir uno.

### Opción A — Twilio (la más rápida para probar)

1. Crear una cuenta en Twilio y abrir **Messaging → Try it out → Send a WhatsApp message**.
2. Cada teléfono que vaya a recibir mensajes de prueba debe enviar por WhatsApp el texto `join <palabra-clave>` que muestra la consola al número del sandbox. La unión vence al cabo de unos días: si los mensajes dejan de llegar, volver a enviarlo.
3. En `Back/.env`:

   ```dotenv
   WHATSAPP_PROVIDER=twilio
   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
   ```

   `TWILIO_WHATSAPP_FROM` es el número del sandbox que muestra la consola (puede ser otro en cuentas nuevas).
4. En producción, con un remitente de WhatsApp aprobado, crear las plantillas en **Content Template Builder** y cargar `TWILIO_CONTENT_SID_NUEVO_ENVIO` y `TWILIO_CONTENT_SID_VISITA_FALLIDA`. Con esos valores se envía la plantilla en lugar del texto libre.

### Opción B — Meta WhatsApp Cloud API

1. En <https://developers.facebook.com> crear una app de tipo **Business** y agregarle el producto **WhatsApp**.
2. En **WhatsApp → API Setup** copiar el **Phone number ID** del número de prueba y agregar los teléfonos destinatarios permitidos (el número de prueba solo entrega a esa lista).
3. El token temporal de esa pantalla vence a las 24 horas. Para algo estable, crear un **usuario del sistema** en la configuración del negocio con el permiso `whatsapp_business_messaging` y generar su token.
4. En **WhatsApp Manager → Plantillas de mensajes** crear dos plantillas de categoría **Utilidad**, idioma **Spanish (ARG)**:

   | Plantilla | Cuerpo sugerido | Parámetros que envía el sistema |
   |---|---|---|
   | `token_seguimiento` | `Hola {{1}}, se registró un envío en Gestión de Envíos. Tu código de seguimiento es {{2}}. Consultá su estado en {{3}}` | nombre, código `ENV-…`, enlace |
   | `aviso_visita` | `Hola {{1}}, visitamos tu domicilio pero no pudimos entregar el paquete {{2}}. Consultá el estado del envío en {{3}}` | nombre, número `PAQ-…`, enlace |

5. En `Back/.env`:

   ```dotenv
   WHATSAPP_PROVIDER=meta
   WHATSAPP_META_TOKEN=EAAG...
   WHATSAPP_META_PHONE_NUMBER_ID=123456789012345
   WHATSAPP_META_PLANTILLA_NUEVO_ENVIO=token_seguimiento
   WHATSAPP_META_PLANTILLA_VISITA_FALLIDA=aviso_visita
   WHATSAPP_META_IDIOMA_PLANTILLA=es_AR
   ```

   Si las plantillas quedan vacías se envía texto libre, que Meta solo entrega dentro de la ventana de 24 horas.

### Teléfonos

Los teléfonos se cargan como texto libre en el registro del envío. Antes de enviar se normalizan al formato internacional de celular de WhatsApp: para Argentina `+549` + código de área + número, quitando el `0` y el `15` (`03564 15 445566` → `+5493564445566`). Sin código de país se asume `WHATSAPP_CODIGO_PAIS` (54). Si el número no es utilizable, solo ese aviso queda `FALLIDO` con el motivo.

`WHATSAPP_PROVIDER=deshabilitado` apaga el canal: cada intento queda registrado como `FALLIDO` con ese motivo.

## Comprobar que funciona

1. Reiniciar la API. El log de arranque muestra `Notificaciones: email=gmail, whatsapp=twilio` (o los proveedores elegidos).
2. Registrar un envío desde `/envios/nuevo` con un email y un teléfono propios (el teléfono debe estar unido al sandbox o en la lista permitida de Meta).
3. En **Recepción en terminal**, escanear o tipear el `PAQ-…`: el panel **Avisos al cliente** muestra el resultado de los cuatro intentos y el motivo de cada fallo. **Reenviar avisos no enviados** reintenta solo los que fallaron.
4. Por API: `GET /api/v1/envios/{token}/notificaciones` y `POST /api/v1/envios/{token}/notificaciones/reintentar` (roles `VENDEDOR`, `ADMINISTRATIVO` o `SUPERADMIN`).

Los errores guardados incluyen el código del proveedor (por ejemplo `131030`, número no permitido en Meta, o `63007`, remitente inexistente en Twilio), nunca el token ni la contraseña.
