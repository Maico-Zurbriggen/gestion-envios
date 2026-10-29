# HU05 — Avisos al cliente por email y WhatsApp

> Yo como remitente o destinatario deseo recibir el código de seguimiento y las novedades del envío, para saber en qué estado está sin tener que consultarlo.

Sprint 2. HU05 cubre el aviso del token; los avisos de cada etapa y los plazos se agregaron con [HU14](./hu14-plazos-y-avisos.md), y este documento describe el mecanismo común. Configuración de proveedores: [notificaciones-email-whatsapp.md](../02-configuracion/notificaciones-email-whatsapp.md). Momento de cada aviso: [circuito logístico](../../../knowledge/circuito-logistico.md).

## Qué se avisa y a quién

| Momento | Aviso | Destinatarios |
|---|---|---|
| Alta del envío (HU03) | Código de seguimiento y enlace público, con el plazo para llevarlo a la sucursal | Remitente y destinatario |
| Admisión en sucursal (HU06) | Admitido | Remitente |
| Salida a reparto (HU10 y HU11) | Sale a reparto | Destinatario |
| Listo para retirar (admisión en la sucursal de retiro, llegada del recorrido entre sucursales o visitas agotadas) | Listo para retirar | Destinatario |
| Entrega a domicilio o retiro (HU12 y HU13) | Entregado | Remitente y destinatario |
| Visita fallida (HU12) | Visita fallida y próximo paso | Destinatario |
| Retiro vencido | Devolución | Remitente |
| Registro sin llevar a una sucursal en 10 días | Registro vencido | Remitente |

En una devolución, los avisos van solo al remitente. La lista de hitos está en `HITOS`, en [`servicio_notificaciones.py`](../../app/application/services/servicio_notificaciones.py).

## Cómo se envía

- **Canales:** cada aviso sale por email y por WhatsApp. El fallo de un canal no afecta al otro ni a la operación que lo originó: los avisos se despachan en segundo plano, después de confirmar la operación.
- **Una vez por envío:** un mismo hito se avisa una sola vez por envío, canal y destinatario dentro de 12 horas (`VENTANA_AVISO_HITO`). Los bultos del mismo envío generan un único aviso que nombra los paquetes.
- **Sin duplicados:** una reserva atómica, con vencimiento de 5 minutos, impide despachar dos veces el mismo intento. Un intento `ENVIADO` nunca se repite.
- **Textos:** cada correo usa su plantilla estándar ([`domain/rules/plantillas_correo.py`](../../app/domain/rules/plantillas_correo.py)) con el diseño de la marca. Todo dato del envío se escapa antes de ir al HTML. Los mensajes no incluyen documentos ni teléfonos: solo el código y el enlace de seguimiento.
- **WhatsApp:** los teléfonos se normalizan a E.164 de celular ([`telefono_rules.py`](../../app/domain/rules/telefono_rules.py)). Con plantilla aprobada se usa la plantilla; sin ella se envía texto libre, que Meta solo entrega dentro de la ventana de 24 horas.

## Endpoints

| Método | Ruta | Roles |
|:---|:---|:---|
| `GET` | `/api/v1/envios/{token}/notificaciones` | `VENDEDOR`, `ADMINISTRATIVO`, `SUPERADMIN` |
| `POST` | `/api/v1/envios/{token}/notificaciones/reintentar` | `VENDEDOR`, `ADMINISTRATIVO`, `SUPERADMIN` |

El primero lista cada intento con su canal, destinatario, estado y error. El segundo reintenta los que no se enviaron. En el frontend se usan desde el panel «Avisos al cliente» de la recepción en terminal y desde la trazabilidad del monitor.

## Persistencia

Cada intento es una fila de `notificaciones_envio`: canal, destinatario, estado, `tipo_aviso` y `paquete_id`. Los errores guardados nunca contienen credenciales.

## Pruebas

[`tests/integration/test_hu05_notificaciones.py`](../../tests/integration/test_hu05_notificaciones.py) y las pruebas de proveedores y de normalización de teléfonos en `tests/unit/`.
