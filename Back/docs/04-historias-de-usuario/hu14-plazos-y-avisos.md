# HU14 — Plazos y avisos del envío

> Yo como emisor y destinatario deseo recibir un aviso en cada etapa del envío y conocer los plazos para llevar y retirar el paquete, para saber en qué estado está y no perderlo por un plazo vencido.

Sprint 2 · Prioridad: **Alta** · Estimación: **5 SP**. Amplía los canales de [HU05](./hu05-notificaciones.md) y el retiro de [HU13](./hu13-retiro-sucursal.md). Momento de cada aviso y de cada plazo: [circuito logístico](../../../knowledge/circuito-logistico.md).

## Criterios de aceptación

1. **Aviso de cada etapa.** Cuando el envío cambia de etapa (admitido, sale a reparto, listo para retirar, entregado, visita fallida, devolución o registro vencido), se avisa por email y WhatsApp a quien corresponde, una sola vez por envío.
2. **Plazo de retiro vencido.** Si el paquete no se retira en 7 días hábiles desde que queda listo, vuelve a su sucursal de origen para devolverlo al remitente, y se le avisa.
3. **Registro vencido.** Si el envío no se lleva a ninguna sucursal en 10 días desde el registro, el registro vence y se avisa al remitente.

## Implementación

- **Avisos:** la lista de hitos y sus destinatarios está en `HITOS`, en [`servicio_notificaciones.py`](../../app/application/services/servicio_notificaciones.py). Cada hito se avisa una vez por envío, canal y destinatario dentro de 12 horas; el detalle está en [HU05](./hu05-notificaciones.md).
- **Plantillas:** una plantilla estándar por aviso, con el diseño de la marca ([`plantillas_correo.py`](../../app/domain/rules/plantillas_correo.py)).
- **Plazos:** las reglas `pre_registro_vencido`, `retiro_vencido` y `sumar_dias_habiles` (lunes a viernes) están en [`circuito_rules.py`](../../app/domain/rules/circuito_rules.py). `ServicioPlazos` las aplica.
- **Revisión automática:** la API revisa los plazos cada `INTERVALO_PLAZOS_MINUTOS` (30 por defecto). `POST /api/v1/admin/monitor/procesar-plazos` la ejecuta en el momento.
- **Devolución:** en una devolución, los avisos van solo al remitente, y en la sucursal de origen retira el remitente ([HU13](./hu13-retiro-sucursal.md)).

## Pruebas

[`tests/integration/test_circuito_logistico.py`](../../tests/integration/test_circuito_logistico.py) y [`tests/integration/test_hu05_notificaciones.py`](../../tests/integration/test_hu05_notificaciones.py).
