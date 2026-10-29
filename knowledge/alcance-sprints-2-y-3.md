# Alcance de los sprints 2 y 3

No hay Sprint 4. Lo que se sumó después del cierre del Sprint 2 se reparte entre los dos sprints como **criterios refinados de sus propias historias**, no como historias nuevas. Lo que no era necesario para cumplirlas quedó fuera del alcance.

El código anterior al recorte se conserva en la rama `extras-post-sprint3`.

## Sprint 2: HU05, HU06, HU09 y HU13

| Historia | Criterios refinados | Documentación |
|---|---|---|
| **HU05**: avisos al cliente | Además del código de seguimiento, se avisa cada hito del envío por email y WhatsApp: admitido, sale a reparto, listo para retirar, entregado, visita fallida, devolución y registro vencido. Se avisa una vez por envío, no por bulto. Cada correo usa su plantilla estándar con el diseño de la marca. | [hu05-notificaciones.md](../Back/docs/04-historias-de-usuario/hu05-notificaciones.md), [circuito-logistico.md](./circuito-logistico.md) |
| **HU06**: recepción en terminal | El envío declara la sucursal donde se va a llevar (`sucursal_origen_id`). Se recibe en la sucursal en la que trabaja el operador. Se puede escanear con el celular, registrar el peso en balanza e imprimir la etiqueta térmica al admitir. | [hu06-recepcion-terminal.md](../Back/docs/04-historias-de-usuario/hu06-recepcion-terminal.md), [escaner-etiquetas.md](./escaner-etiquetas.md) |
| **HU09**: sucursales para retiro | El catálogo público muestra solo las sucursales activas. El Superadministrador da de alta y edita sucursales con su dirección y ubicación, que son el punto de partida de los recorridos. | [hu09-sucursales-retiro.md](../Back/docs/04-historias-de-usuario/hu09-sucursales-retiro.md), [sucursales-por-usuario.md](./sucursales-por-usuario.md) |
| **HU13**: retiro verificado | Se entrega en la sucursal en la que trabaja el operador. El retiro tiene un plazo de 7 días hábiles y, si vence, el paquete vuelve al remitente. Un registro que no se lleva a una sucursal en 10 días vence. | [hu13-retiro-sucursal.md](../Back/docs/04-historias-de-usuario/hu13-retiro-sucursal.md), [circuito-logistico.md](./circuito-logistico.md) |

**Acceso por sucursal.** Al cerrar el Sprint 2 quedaba un límite: el operador elegía su sucursal en pantalla y los usuarios no tenían sucursal asignada. Se resuelve como criterio común de HU06 y HU13:

- cada usuario pertenece a sus sucursales;
- después del login elige en cuál trabaja;
- el backend rechaza lo que corresponde a otra sucursal.

Para asignarlas, la administración de usuarios suma la edición, la baja y el blanqueo de contraseña. Detalle en [sucursales-por-usuario.md](./sucursales-por-usuario.md).

## Sprint 3: HU07, HU08, HU10, HU11 y HU12

| Historia | Criterios refinados | Documentación |
|---|---|---|
| **HU07**: reclamos | El personal revisa, responde y cierra los reclamos desde Monitor › Reclamos. | [reclamos-preguntas-recorridos.md](./reclamos-preguntas-recorridos.md), [monitor.md](./monitor.md) |
| **HU08**: preguntas frecuentes | Sin cambios. | [reclamos-preguntas-recorridos.md](./reclamos-preguntas-recorridos.md) |
| **HU10**: recorridos | Los recorridos se arman como hojas de ruta de la sucursal activa, sobre un mapa con el recorrido real por calles. El orden se calcula por el camino más rápido, con «Optimizar recorrido» en el armado y al crear. Para ver el estado de los paquetes, Monitor › Paquetes ofrece el listado por etapa y la trazabilidad. | [hu10-recorridos.md](../Back/docs/04-historias-de-usuario/hu10-recorridos.md), [mapas.md](./mapas.md), [monitor.md](./monitor.md) |
| **HU11**: reparto | La app del repartidor permite optimizar el orden desde su posición. En los recorridos entre sucursales, marca «Llegué a [sucursal]» en cada parada, en orden, y así se actualizan el recorrido y el seguimiento. | [hu11-hu12-reparto.md](../Back/docs/04-historias-de-usuario/hu11-hu12-reparto.md), [circuito-logistico.md](./circuito-logistico.md) |
| **HU12**: entrega a domicilio | Hay como máximo 2 visitas. Después, el paquete queda para retirar en la sucursal, y si no se retira, vuelve al remitente. | [hu11-hu12-reparto.md](../Back/docs/04-historias-de-usuario/hu11-hu12-reparto.md), [circuito-logistico.md](./circuito-logistico.md) |

**Tarea técnica de calidad (sin historia propia):**
- la identidad visual compartida con las otras apps: barra lateral, transiciones entre secciones y esqueletos de carga;
- la limpieza de código sin uso;
- la optimización de la carga inicial.

## Fuera del alcance

- **Control de carga y descarga por escaneo.** La llegada a cada sucursal la marca el repartidor desde su celular.
- **Tablero de indicadores del Monitor, sección Incidencias y exportación a CSV.** El Monitor queda con el listado por etapa, la trazabilidad y los reclamos.

## Base de datos

- Neon está en `d2a6f81112ac` (HU11 y HU12).
- Quedan dos migraciones por aplicar, en este orden:
  1. `c41a7e9d2b55`: circuito logístico.
  2. `e5b19c3a7d20`: sucursales por usuario.
