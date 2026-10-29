# HU13 — Retiro verificado en sucursal

> Yo como personal de la sucursal deseo verificar la identidad de quien retira un paquete y registrar el retiro, para entregarlo solo a quien corresponde y dejar constancia.

Sprint 2. Plazos y devoluciones: [circuito logístico](../../../knowledge/circuito-logistico.md). Acceso por sucursal: [sucursales por usuario](../../../knowledge/sucursales-por-usuario.md).

## Endpoints

| Método | Ruta | Roles |
|:---|:---|:---|
| `GET` | `/api/v1/sucursal/paquetes/{id_o_codigo}/validar-retiro` | `ADMINISTRATIVO`, `SUPERADMIN` |
| `POST` | `/api/v1/sucursal/paquetes/{id}/registrar-retiro` | `ADMINISTRATIVO`, `SUPERADMIN` |

Router: [`app/api/v1/routers/sucursal_retiro.py`](../../app/api/v1/routers/sucursal_retiro.py). En el frontend: Registrar retiro (`/sucursal/retiros`).

## Reglas

- **Estado:** solo se retiran paquetes en `LISTO_PARA_RETIRO`, `EN_SUCURSAL` o `EN_SUCURSAL_DESTINO`.
- **Sucursal:** el envío tiene que ser de retiro en sucursal, salvo un envío a domicilio que agotó sus visitas o una devolución. El paquete tiene que estar en su sucursal de retiro, y esa tiene que ser la sucursal en la que trabaja el operador (`sucursal_id`). Si el operador no la tiene habilitada, la respuesta es `403`.
- **Quién retira:**
  - el destinatario;
  - un tercero autorizado, con su propio documento, copia del documento del titular y nota de autorización;
  - en una devolución, el remitente.
- **Identidad:** quien retira tiene que ser mayor de 16 años según su fecha de nacimiento (`receptor_fecha_nacimiento`). El personal confirma que vio el documento original (`documento_original_verificado`).
- **Concurrencia:** la transición es condicional. Si dos retiros llegan a la vez, se registra uno solo; el otro recibe `409`.

## Plazos

- **Retiro:** el paquete tiene 7 días hábiles para retirarse desde que queda listo (`PLAZO_RETIRO_DIAS_HABILES`). La fecha límite (`paquetes.retiro_hasta`) se ve en el seguimiento público, en la pantalla de retiro y en el monitor.
- **Vencimiento:** si el plazo vence, el paquete pasa a devolución y vuelve a su sucursal de origen para que lo retire el remitente. Al retirarlo, queda `DEVUELTO`.
- **Revisión automática:** los plazos se revisan solos cada 30 minutos (`ServicioPlazos`).

## Constancia

El retiro queda en `eventos_entrega` (`tipo_evento = RETIRO_SUCURSAL`) con:

- quién retiró, su documento y su fecha de nacimiento;
- la verificación documental;
- el operador y la sucursal;
- la fecha y hora del servidor.

Se avisa «Entregado» al remitente y al destinatario (HU05).

## Pruebas

[`tests/integration/test_hu13_retiro_sucursal.py`](../../tests/integration/test_hu13_retiro_sucursal.py) y los casos de vencimiento y devolución en `tests/integration/test_circuito_logistico.py`.
