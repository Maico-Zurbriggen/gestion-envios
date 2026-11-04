# Alcance de los sprints 2 y 3

No hay Sprint 4. Las historias originales del Product Backlog (HU01 a HU13) quedan en el sprint donde estaban planificadas. Lo que se sumó después se reparte entre los sprints 2 y 3 como **historias nuevas**: tres en el Sprint 2 (HU14, HU15 y HU16) y una en el Sprint 3 (HU17). Las mejoras que implementan escenarios ya existentes de HU10, HU11 y HU12 quedan como tareas de esas historias. Lo que no era necesario quedó fuera del alcance.

El código anterior al recorte se conserva en la rama `extras-post-sprint3`.

## Esfuerzo

| Sprint | Historias | Story Points | Tareas | Horas |
|---|---|---|---|---|
| 2 | HU05, HU06, HU09, HU13 y las nuevas HU14, HU15, HU16, más calidad y revisión | 41 | 54 | 241 |
| 3 | HU07, HU08, HU10, HU11, HU12 y la nueva HU17, más cierre | 53 | 57 | 298 |

El reparto deja los dos sprints lo más parejos posible sin mover las historias originales. El Sprint 3 no puede bajar de unas 298 h porque sus historias originales suman 248 h, y lo que depende del reparto o de HU07 tiene que ir ahí.

**Riesgo:** el Sprint 2 está planificado para una semana. Con 241 h y cuatro integrantes, la carga es de unas 12 h por persona y día, así que hay que confirmar la disponibilidad del equipo. El Sprint 3, de dos semanas, queda en unas 7,5 h por persona y día.

Fuentes: `Pila Sprint 2 Gestion Envios (v2).xlsm` y `Pila_Sprint_3_Gestion_Envios (v2).xlsm`.

## Sprint 2

| Historia | Qué incluye | SP | Horas | Documentación |
|---|---|---|---|---|
| HU05, HU06, HU09 y HU13 | Sin cambios respecto del plan original. | 23 | 113 | [Back/docs](../Back/docs/04-historias-de-usuario/) |
| **HU14**: plazos y avisos del envío | Aviso de cada etapa del envío por email y WhatsApp, una vez por envío, con plantillas estándar de la marca. El retiro tiene 7 días hábiles y, si vence, el paquete vuelve al remitente. Un registro que no se lleva a una sucursal en 10 días vence. | 5 | 28 | [hu14-plazos-y-avisos.md](../Back/docs/04-historias-de-usuario/hu14-plazos-y-avisos.md), [circuito-logistico.md](./circuito-logistico.md) |
| **HU15**: admisión y control en la sucursal | Sucursal de origen obligatoria, escáner con el celular, peso en balanza y etiqueta térmica al admitir. Monitor › Paquetes con el listado por etapa y la trazabilidad. | 5 | 32 | [hu15-admision-y-control.md](../Back/docs/04-historias-de-usuario/hu15-admision-y-control.md), [escaner-etiquetas.md](./escaner-etiquetas.md), [monitor.md](./monitor.md) |
| **HU16**: sucursales y acceso por sucursal | Alta y edición de sucursales con ubicación, usuarios con sus sucursales, sucursal activa y control en el servidor. | 8 | 42 | [hu16-sucursales-y-acceso.md](../Back/docs/04-historias-de-usuario/hu16-sucursales-y-acceso.md), [sucursales-por-usuario.md](./sucursales-por-usuario.md) |
| Calidad transversal (tarea técnica, sin SP) | Identidad visual compartida con las otras apps (barra lateral, transiciones y esqueletos de carga), limpieza de código sin uso y optimización de la carga inicial. | — | 20 | [visual-identity.md](./visual-identity.md) |
| Revisión integrada | Flujo completo y demostración. | — | 6 | |

## Sprint 3

| Historia | Qué incluye | SP | Horas | Documentación |
|---|---|---|---|---|
| HU07 y HU08 | Sin cambios respecto del plan original. | 8 | 28 | [reclamos-preguntas-recorridos.md](./reclamos-preguntas-recorridos.md) |
| HU10 | Además de lo planificado, implementa sus escenarios E1 y E2 con hojas de ruta, mapa por calles y «Optimizar recorrido» por tiempos. | 21 | 100 | [hu10-recorridos.md](../Back/docs/04-historias-de-usuario/hu10-recorridos.md), [mapas.md](./mapas.md) |
| HU11 | Optimizar el orden desde el celular. En los recorridos entre sucursales, la llegada se registra sola a 10 km de cada sucursal (E3); si el GPS no la registró, el repartidor la marca con «Llegué a [sucursal]», en orden. | 13 | 60 | [hu11-hu12-reparto.md](../Back/docs/04-historias-de-usuario/hu11-hu12-reparto.md) |
| HU12 | Como máximo 2 visitas (E3). Después, el paquete queda para retirar en la sucursal y, si no se retira, vuelve al remitente. | 8 | 44 | [hu11-hu12-reparto.md](../Back/docs/04-historias-de-usuario/hu11-hu12-reparto.md), [circuito-logistico.md](./circuito-logistico.md) |
| **HU17**: bandeja interna de reclamos | Revisar, responder y cerrar reclamos desde Monitor › Reclamos, solo los de la sucursal activa. | 3 | 10 | [hu17-bandeja-reclamos.md](../Back/docs/04-historias-de-usuario/hu17-bandeja-reclamos.md), [monitor.md](./monitor.md) |
| Cierre e integración | Pruebas de punta a punta, correcciones y entrega. | — | 56 | |

## Fuera del alcance

- **Control de carga y descarga por escaneo.** La llegada a cada sucursal se registra por proximidad, con el botón del repartidor como respaldo.
- **Tablero de indicadores del Monitor, sección Incidencias y exportación a CSV.** El Monitor queda con el listado por etapa, la trazabilidad y los reclamos.

## Base de datos

- Neon está en `d2a6f81112ac` (HU11 y HU12).
- Quedan dos migraciones por aplicar, en este orden:
  1. `c41a7e9d2b55`: circuito logístico (HU14 y HU15).
  2. `e5b19c3a7d20`: sucursales por usuario (HU16).
