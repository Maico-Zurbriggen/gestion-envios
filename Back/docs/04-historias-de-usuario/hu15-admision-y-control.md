# HU15 — Admisión y control en la sucursal

> Yo como vendedor o personal de la terminal deseo admitir el paquete en la sucursal donde se lleva, con su peso y etiqueta, y ver los paquetes de la sucursal por etapa, para dejar constancia física de cada uno y controlar dónde está.

Sprint 2 · Prioridad: **Alta** · Estimación: **5 SP**. Amplía la recepción de [HU06](./hu06-recepcion-terminal.md).

## Criterios de aceptación

1. **Sucursal de origen.** Al registrar el envío se elige la sucursal donde se va a llevar; solo esa sucursal puede admitirlo.
2. **Admisión con peso y etiqueta.** Al escanear el paquete, con lector o con la cámara del celular, y registrar el peso, se admite, se advierte una diferencia mayor al 10 % con lo declarado y se imprime la etiqueta.
3. **Paquetes por etapa.** El personal ve los paquetes de su sucursal por etapa y la trazabilidad de cada uno.

## Implementación

- **Sucursal de origen:** `envios.sucursal_origen_id`. La recepción la valida en el servidor ([HU06](./hu06-recepcion-terminal.md)).
- **Escáner y etiquetas:** cámara con BarcodeDetector o ZXing y perfiles de impresora térmica. Detalle en [escáner y etiquetas](../../../knowledge/escaner-etiquetas.md).
- **Monitor:** `GET /api/v1/admin/monitor/paquetes` (listado por etapa, con filtros) y `GET /api/v1/admin/monitor/paquetes/{numero_paquete}` (trazabilidad), en [`monitor.py`](../../app/api/v1/routers/monitor.py). En el frontend: Monitor › Paquetes. Detalle en [monitor](../../../knowledge/monitor.md).

## Pruebas

[`tests/integration/test_hu06_recepcion_terminal.py`](../../tests/integration/test_hu06_recepcion_terminal.py) y [`tests/integration/test_monitor.py`](../../tests/integration/test_monitor.py).
