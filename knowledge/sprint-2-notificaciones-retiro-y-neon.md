# Sprint 2: notificaciones, recepción, retiro y base Neon

Cambios y decisiones del 27 de octubre de 2026 (rama `sprint-2-cambios-y-arreglos`) para completar HU05, HU06, HU09 y HU13 según el Sprint Backlog 2, y para que la base compartida de Neon no vuelva a quedar desactualizada.

## HU05 — Token por email y WhatsApp

- Se envía el código de seguimiento y el enlace público por **email y WhatsApp al remitente y al destinatario** (cuatro intentos por envío). La decisión anterior de "solo email" (registrada en la [auditoría del Sprint 3](auditoria-sprint-3.md)) queda reemplazada: el Product Backlog pide ambos canales y el usuario lo solicitó explícitamente.
- La visita fallida de HU12 también avisa por los dos canales.
- Proveedores intercambiables por configuración: email `mock`, `gmail` o `smtp`; WhatsApp `mock`, `twilio`, `meta` o `deshabilitado`. Por defecto son `mock`, así que nada sale a internet sin configurarlo. Guía: [`Back/docs/02-configuracion/notificaciones-email-whatsapp.md`](../Back/docs/02-configuracion/notificaciones-email-whatsapp.md).
- Puertos `IEmailProvider` e `IWhatsAppProvider` en `application/interfaces/proveedores_mensajeria.py`; adaptadores en `infrastructure/email` e `infrastructure/whatsapp`; textos en la regla pura `domain/rules/notificacion_rules.py` (escapa HTML, no incluye documentos ni teléfonos).
- Teléfonos normalizados a E.164 de celular (`domain/rules/telefono_rules.py`; Argentina: `+549`, sin `0` ni `15`).
- Demo de Meta: entrega real comprobada de los textos de seguimiento y visita fallida a un destinatario verificado, dentro de la ventana de 24 horas iniciada por ese destinatario. Si la lista de prueba de Meta guarda un formato distinto del E.164, `WHATSAPP_META_DESTINATARIOS_PRUEBA` declara equivalencias explícitas en el adaptador; no cambia la normalización del dominio. Los tokens tienen vencimiento y los números de prueba admiten hasta cinco destinatarios. La prueba Trial actual de Twilio no admite los textos personalizados del proyecto.
- Cada intento es una fila de `notificaciones_envio`. Un fallo de un canal no afecta a los demás ni al alta. Una reserva atómica (con vencimiento de 5 minutos) impide despachos duplicados y un intento `ENVIADO` nunca se repite. Los errores guardados no contienen credenciales.
- Personal (`VENDEDOR`, `ADMINISTRATIVO`, `SUPERADMIN`): `GET /api/v1/envios/{token}/notificaciones` y `POST …/reintentar`. En el frontend, el panel **Avisos al cliente** de la recepción en terminal (`features/notifications/`).

## HU06 — Recepción en terminal

- Si el envío se retira en sucursal y se recibe en esa misma sucursal, el paquete pasa directo a `LISTO_PARA_RETIRO`. Antes quedaba en `EN_SUCURSAL_ORIGEN` sin salida: HU10 no lo despacha y HU13 no lo acepta.
- La transición es un `UPDATE … WHERE estado IN (…)`: dos confirmaciones simultáneas registran una sola recepción; la otra recibe `409`.
- Frontend: tras confirmar, el campo de código queda vacío y con foco para el siguiente escaneo; botón **Procesar otro paquete**; mensaje específico para códigos inexistentes; estados con texto legible; la sucursal elegida se recuerda en el navegador.

## HU13 — Retiro verificado (reglas en el backend)

- Solo se retiran paquetes en `LISTO_PARA_RETIRO`, `EN_SUCURSAL` o `EN_SUCURSAL_DESTINO`; se quitó `Pendiente`.
- El envío debe ser de retiro en sucursal, el paquete debe estar en la sucursal elegida y el operador debe indicar su sucursal (`sucursal_id`), que tiene que coincidir.
- Quien retira debe ser **mayor de 16 años** según su fecha de nacimiento (`receptor_fecha_nacimiento`, misma regla estricta que HU12) y el personal confirma el documento original (`documento_original_verificado`). Un tercero presenta su propio documento, que debe coincidir con el de la autorización.
- La constancia guarda fecha de nacimiento, verificación documental real (ya no un `True` fijo), operador, sucursal y fecha y hora. Transición condicional contra retiros simultáneos (`409`).
- Frontend: `pickupApi.ts` reutiliza `operationalRequest` y mapea las sucursales a camelCase.

## HU09 y HU04 — Seguimiento

- `GET /seguimiento/{token}` incluye `tipo_entrega`. Con retiro en sucursal, la vista pública consulta `/sucursales/opciones-retiro/{token}` y muestra la sucursal asignada, la disponibilidad por paquete y qué llevar.
- Etapas visuales según la modalidad: con retiro en sucursal son cinco (registrado, recibido, en viaje, para retirar, retirado); la llegada a la sucursal de destino ya no retrocede a "En sucursal".
- El historial público describe recepción, viaje, disponibilidad y retiro sin datos personales.

## Navegación del panel

- "Registrar envío", "Seguir envío", "Sucursales" y "Preguntas frecuentes" son públicas y estaban fuera del layout: al entrar desde el menú se perdía el panel lateral. Ahora `layouts/PublicPageLayout.tsx` las muestra dentro de `MainLayout` cuando hay sesión (sin su encabezado público duplicado, vía `useInsidePanel`) y sueltas, como antes, para clientes sin sesión.
- Verificación: `tests/panel-navigation.mjs` (Vite en `localhost:5173` y Chrome con CDP en 9227) recorre las secciones por URL y con clics del menú.

## Base de datos Neon

- La API ya no usa `create_all`. Al arrancar aplica `alembic upgrade head` (con candado asesor en PostgreSQL) y adopta bases creadas antes con `create_all`.
- `python -m app.infrastructure.db.actualizar_base [--verificar] [--database-url …] [--semillas]` actualiza o verifica cualquier base; acepta el connection string de Neon sin editar y usa el endpoint directo para el DDL.
- `.github/workflows/ci-neon.yml` verifica front y back en cada push y, en `development` y `main`, aplica las migraciones a Neon con el secreto `NEON_DATABASE_URL`.
- Una prueba falla si se cambia `models.py` sin migración. Detalle: [`Back/docs/02-configuracion/base-de-datos-neon.md`](../Back/docs/02-configuracion/base-de-datos-neon.md).

## Verificación

- Backend: `pip check` sin problemas, Ruff sin observaciones y 444 pruebas aprobadas (incluye proveedores con transporte simulado, normalización de teléfonos, carreras de recepción y retiro y adopción de bases heredadas).
- Frontend: `npm run lint`, `npm run build` y `npm test` aprobados. `tests/sprint3-browser.mjs` suma la consulta y el reenvío de avisos (HU05), el campo vacío tras recibir (HU06) y la sucursal de retiro en el seguimiento (HU09) a 320 px.
- Flujo real por HTTP contra la API con una copia de la base local: alta → cuatro avisos → recepción en la sucursal de retiro (`LISTO_PARA_RETIRO`) → segunda recepción rechazada → seguimiento y opciones de retiro → retiro inválido rechazado → retiro válido → segundo retiro rechazado.

## Límites

- No se verificó la entrega real por Gmail ni de los avisos personalizados por Twilio. Meta se verificó con recursos de prueba; eso no valida un remitente ni plantillas de producción. Las credenciales no se incluyen en el repositorio y cada proveedor mantiene sus condiciones de envío.
- No se ejecutaron migraciones contra Neon desde esta rama: falta configurar `NEON_DATABASE_URL` o correr el comando con el connection string.
- La sucursal del operador se elige en pantalla; los usuarios todavía no tienen sucursal asignada en el modelo. **Resuelto después** como criterio refinado de HU06 y HU13: ver [Alcance de los sprints 2 y 3](alcance-sprints-2-y-3.md) y [Sucursales por usuario](sucursales-por-usuario.md).
