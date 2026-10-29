# Circuito logístico: del registro a la entrega

Cómo viaja un paquete desde que el cliente lo registra hasta que lo recibe. El circuito toma como referencia a Correo Argentino y Andreani y lo adapta a esta operación.

## Resumen

| Etapa | Quién | Estado del paquete | Aviso al cliente |
|---|---|---|---|
| 1. Registro web | Cliente | `Pendiente` | Código de seguimiento al remitente y al destinatario, con el plazo para llevarlo. |
| 2. Admisión en sucursal | Vendedor | `EN_SUCURSAL_ORIGEN` (o `LISTO_PARA_RETIRO` si se retira en la misma sucursal) | «Admitido» al remitente. |
| 3. Viaje entre sucursales | Repartidor de larga distancia | `EN_TRANSITO` | — |
| 4. Llegada a la sucursal | El repartidor la marca desde el celular | `LISTO_PARA_RETIRO` o `EN_SUCURSAL_DESTINO` | «Listo para retirar» al destinatario. |
| 5a. Reparto a domicilio | Repartidor de corta distancia | `EN_REPARTO` → `ENTREGADO` o `ENTREGA_FALLIDA` | «Sale a reparto», «Entregado» o «Visita fallida». |
| 5b. Retiro en sucursal | Vendedor | `ENTREGADO_EN_SUCURSAL` | «Entregado» al remitente y al destinatario. |
| Devolución | Sistema | `EN_DEVOLUCION` → `LISTO_PARA_RETIRO` en el origen → `DEVUELTO` | «Devolución» al remitente. |
| Vencimiento | Sistema | `VENCIDO` | «Registro vencido» al remitente. |

## 1. Registro web (pre-registro)

- El cliente registra el envío sin cuenta, elige **a qué sucursal lo va a llevar** (`sucursal_origen_id`, obligatoria) y recibe el código de seguimiento (`ENV-…`) y un comprobante con un código de barras por paquete. En el mostrador, la sucursal de origen es la sucursal activa.
- **El cliente no imprime etiquetas.** La etiqueta térmica la imprime la sucursal al admitir el paquete. El comprobante puede mostrarse en el celular o impreso en una hoja común.
- El registro tiene **10 días corridos** para llevarse a una sucursal (`VENCIMIENTO_PRE_REGISTRO_DIAS`). La respuesta del alta informa la fecha límite (`admitir_hasta`).
- El botón «Imprimir etiquetas (mostrador)» del resultado aparece solo para el personal (`VENDEDOR`, `ADMINISTRATIVO` y `SUPERADMIN`), que registra envíos en el mostrador.

## 2. Admisión en la sucursal de origen

Pantalla: Recibir paquetes (`/terminal/recepcion`).

1. Se escanea el comprobante o se escribe el número de paquete. La pantalla indica el bulto («2 de 3»).
2. **Peso en balanza** (opcional): si difiere del declarado en más de un 10 %, se muestra un aviso para cobrar la diferencia o corregir el envío. El peso queda en `paquetes.peso_admision_kg`.
3. Al confirmar, se registra la **sucursal de origen** (`paquetes.sucursal_origen_id`) y, si la casilla está marcada, se imprime la etiqueta al instante. La casilla se recuerda por puesto (`terminal-imprimir-al-admitir`).
4. Se avisa al remitente («Admitido»).

Reglas:

- Un registro `VENCIDO` no se admite: hay que registrar el envío de nuevo.
- Si el paquete se retira en la misma sucursal donde se admite, queda directamente `LISTO_PARA_RETIRO`, con su plazo de retiro, y se avisa al destinatario.

## 3. Viaje entre sucursales

- El planificador arma recorridos de larga distancia con los paquetes listos para despacho, incluidas las devoluciones (`EN_DEVOLUCION`), que viajan hacia la sucursal de origen.
- Al iniciar el recorrido, los paquetes pasan a `EN_TRANSITO`. El GPS del celular muestra al repartidor en el mapa, pero no cambia estados.

## 4. Llegada a la sucursal, marcada por el repartidor

En la app del repartidor (`/reparto`), un recorrido entre sucursales en curso muestra la **próxima sucursal** y el botón «Llegué a [sucursal]», con confirmación.

- Las sucursales se marcan en orden: solo se puede marcar la próxima con paquetes pendientes.
- Al confirmar, cada paquete que baja ahí queda:
  - `LISTO_PARA_RETIRO`, con fecha límite (`paquetes.retiro_hasta`), si se retira ahí; se avisa al destinatario en ese momento;
  - `EN_SUCURSAL_DESTINO`, si sigue a domicilio;
  - en una devolución, listo para que lo retire el remitente si es su sucursal de origen, o `EN_DEVOLUCION` si sigue viaje.
- El historial queda a nombre del repartidor, con la sucursal y la posición del celular si la comparte. La parada se marca entregada y, cuando no quedan paradas, el recorrido se finaliza.
- API: `POST /api/v1/reparto/recorridos/{id}/llegadas` con `sucursal_id` (y, opcionalmente, `latitud` y `longitud`).

## 5a. Reparto a domicilio

- Al iniciar un recorrido de corta distancia se avisa «Sale a reparto» al destinatario.
- **Máximo 2 visitas** (`MAX_VISITAS_DOMICILIO`). La app muestra «1.ª de 2» o «2.ª de 2» en cada paquete y advierte cuando es la última.
- Después de una visita fallida, el paquete vuelve a la sucursal de origen del recorrido y se incluye en el próximo.
- Si se agotan las visitas, queda `LISTO_PARA_RETIRO` en esa sucursal, con el mismo plazo que cualquier retiro, y el aviso de la visita lo explica.

## 5b. Retiro en sucursal

Pantalla: Registrar retiro (`/sucursal/retiros`).

- **Plazo: 7 días hábiles** desde que queda listo (`PLAZO_RETIRO_DIAS_HABILES`). La fecha límite se ve en el seguimiento público, en la pantalla de retiro y en el monitor.
- Retira el destinatario con DNI o un tercero autorizado. En una devolución, retira el **remitente**.
- También se puede retirar un envío a domicilio que agotó las visitas.

## Plazos automáticos

`ServicioPlazos` revisa cada 30 minutos (`INTERVALO_PLAZOS_MINUTOS`; con `0` se desactiva). También se puede forzar con `POST /api/v1/admin/monitor/procesar-plazos`:

- **Registro vencido:** un paquete `Pendiente` con más de 10 días pasa a `VENCIDO`. Se avisa al remitente una vez por envío.
- **Retiro no realizado:** un paquete esperando con el plazo vencido pasa a devolución:
  - si ya está en su sucursal de origen, queda `LISTO_PARA_RETIRO` para el remitente;
  - si no, pasa a `EN_DEVOLUCION` y viaja de vuelta.

  En los dos casos `paquetes.en_devolucion` queda en verdadero y se avisa al remitente: «Vuelve a vos» si viaja, o «Ya podés retirar el paquete devuelto» si ya está en origen. Cuando el remitente lo retira, el paquete queda `DEVUELTO`.

## Avisos al cliente

Cada hito se avisa por email y WhatsApp a quien corresponde (`HITOS` en `servicio_notificaciones.py`). Cada intento queda auditado en `notificaciones_envio`, con `tipo_aviso` y `paquete_id`.

- **Se avisa por envío, no por bulto.** Un mismo hito se manda una sola vez por envío, canal y destinatario dentro de 12 horas (`VENTANA_AVISO_HITO`). Los bultos que se escanean juntos generan un solo aviso, que nombra los paquetes que están en ese estado. Una segunda salida a reparto al día siguiente vuelve a avisar.
- En una devolución que ya está en la sucursal de origen se manda un solo aviso al remitente: «Ya podés retirar el paquete devuelto».
- Cada aviso por email usa su plantilla estándar (`domain/rules/plantillas_correo.py`), con el diseño de la marca.
- Para WhatsApp por Meta hace falta una plantilla aprobada con 3 variables (nombre, novedad y código), configurada en `WHATSAPP_META_PLANTILLA_AVISO_ESTADO`. En Twilio, el equivalente es `TWILIO_CONTENT_SID_AVISO_ESTADO`. Sin plantilla se envía texto libre, que Meta solo entrega dentro de la ventana de 24 horas.

## Persistencia

Migración `c41a7e9d2b55` (después de `d2a6f81112ac`):

- **`paquetes`:** `sucursal_origen_id`, `peso_admision_kg`, `retiro_hasta` y `en_devolucion`. Completa la sucursal de origen de los paquetes ya admitidos a partir del historial.
- **`notificaciones_envio`:** `tipo_aviso` y `paquete_id`.
