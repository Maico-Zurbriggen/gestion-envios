# Reparto, recepción y seguimiento — HU04, HU06, HU11 y HU12

## Alcance implementado

El 27 de octubre de 2026 se acordó completar las cuatro historias después de la [auditoría del Sprint 3](auditoria-sprint-3.md). Se reutilizan los contratos existentes del backend sin modificar esquema, reglas de negocio, credenciales ni archivos de entorno.

Las features nuevas conservan páginas, componentes, hooks, servicios y tipos propios. TanStack Query administra datos remotos; Redux continúa limitado a sesión. `shared/services/operationalApi.ts` centraliza transporte privado, errores esperados, cancelación y respuestas ilegibles para terminal y reparto. La API se construye desde `VITE_API_URL`, con contratos snake_case y modelos internos camelCase.

## Recepción en terminal (HU06)

- Ruta `/terminal/recepcion`, bajo `ProtectedRoutes`, para `VENDEDOR`, `ADMINISTRATIVO` y `SUPERADMIN`; acceso desde Home y navegación con los mismos roles.
- Identificación por número de paquete o UUID: acepta ingreso manual o lector físico que escribe en el campo y envía Enter. El código se normaliza eliminando espacios y pasando a mayúsculas. No se implementa lectura por cámara.
- Escanear es de solo lectura. Se muestran remitente y documento, destinatario, destino, contenido, peso, dimensiones, observaciones y disponibilidad devueltos por el servidor.
- La confirmación explícita requiere elegir la sucursal donde se recibe físicamente. Admite observaciones de hasta 500 caracteres. Los controles se bloquean durante la operación.
- Los paquetes ya recibidos se muestran con el motivo de indisponibilidad; no ofrecen una segunda recepción. Después de intentar confirmar se actualizan consulta del paquete, seguimiento y gestión de recorridos. Los errores conservan la información necesaria para revisar el estado antes de reintentar.

## Mi reparto (HU11)

- Ruta `/reparto` exclusiva de `REPARTIDOR`, bajo `ProtectedRoutes`; feature cargada de forma diferida.
- Listado de recorridos propios con fecha y estado. Vaciar la fecha permite consultar todos. La fecha inicial es la del navegador del repartidor.
- Detalle con origen, tipo de distancia, progreso por asignaciones, paradas y paquetes en el orden recibido. El inicio pide confirmación y llama al endpoint privado de reparto, sin utilizar permisos administrativos.
- Se reutilizan los tipos y mapeos de recorridos y el recorrido por calles de OSRM ([mapas.md](./mapas.md)), con la posición del vehículo en el mapa. Ante errores de mapas quedan disponibles marcadores, direcciones y lista de paradas; no se inventan trayectos rectos. El enlace de navegación abre el destino elegido en un navegador externo de mapas.
- El GPS se activa por una acción del usuario. Requiere HTTPS o localhost y permiso del navegador. Se informa denegación, ausencia de soporte, timeout y fallas de conexión.
- Se usa `watchPosition`, alta precisión y posiciones sin antigüedad permitida. Se envía como máximo una posición cada diez segundos y no se superponen envíos. Se conserva la última posición confirmada por el servidor con fecha y hora visibles.
- La pantalla debe permanecer abierta: los navegadores móviles pueden suspender ubicación en segundo plano o con el dispositivo bloqueado. Desactivar GPS, cambiar de recorrido, salir de la vista, perder acceso o finalizar elimina el observador y cancela el envío pendiente.
- En larga distancia, a 10 km o menos de la próxima sucursal la llegada se registra sola con la posición (HU11 CA3). Si el GPS no la registró, el repartidor la marca con «Llegué a [sucursal]», en orden y con confirmación (`POST /{id}/llegadas`). En los dos casos se actualizan el detalle, el listado y el seguimiento; si el recorrido finaliza, se detiene el GPS. El detalle activo se actualiza cada quince segundos.

## Resultado de la visita (HU12)

- En recorridos cortos activos, las asignaciones pendientes de paquetes a domicilio en `EN_REPARTO` permiten abrir el formulario. Se consulta el contacto por el endpoint autorizado y se ofrece llamada `tel:` o un mensaje de teléfono ausente.
- Una entrega captura nombre, documento, nacimiento, condición de persona autorizada y firma. Se valida nacimiento contra la fecha UTC y el límite estricto del backend: ser mayor de 16 años; el día del cumpleaños número 16 no alcanza. El backend conserva la validación definitiva.
- Firma dibujada con mouse o puntero táctil en canvas PNG de 720 × 240. Existe alternativa por archivo PNG de hasta 256 KiB y 1024 × 1024 para quien no usa dibujo; se normaliza al canvas antes de enviar. Hay control para limpiar. La firma no se almacena en localStorage, Redux ni seguimiento público.
- La visita fallida exige motivo de 3 a 255 caracteres. La confirmación informa que se solicitó aviso por email sin afirmar que el correo fue entregado.
- Al primer envío se genera un UUID y se conserva una copia inmutable de todos los datos. Ante respuesta perdida o fallo de red, el reintento usa exactamente la misma operación, incluidos UUID y firma. Los campos permanecen bloqueados. Un rechazo de validación permite corregir datos y crear una nueva operación; un conflicto permite volver y revisar el estado actual.
- Conservar la pantalla abierta permite recuperar la misma constancia después de un error. No se persiste la operación sensible para restaurarla después de recargar o cerrar el navegador. Una salida del navegador pierde ese borrador; la API sigue impidiendo una segunda transición del mismo paquete.
- El resultado muestra el identificador y fecha de la constancia. La imagen de firma permanece almacenada por el backend conforme a su contrato. Las consultas afectadas de reparto, logística y seguimiento se invalidan al confirmar.

## Seguimiento público (HU04)

- Contrato extendido con coordenadas de destino, historial y última ubicación por paquete, mapeados a camelCase.
- Mapa compartido `LocationMap` con destino fijo y posiciones que el backend permite publicar. Cada marcador tiene nombre, coordenadas en una lista y fecha para la posición de reparto. No representa un punto antiguo como una medición continua ni publica contactos o firmas.
- Sin coordenadas, se informa ubicación no disponible. Los paquetes en tránsito/reparto habilitan consulta cada quince segundos mientras la vista está activa; no se necesita sesión.
- El historial usa eventos reales. Las cuatro etapas visuales son orientativas y el estado textual del servidor sigue visible. Un mapeo explícito evita que `ENTREGA_FALLIDA` aparezca como entregado; los retiros y entregas en sucursal sí representan estados finales.
- Los errores HTTP 500 muestran un mensaje genérico antes de interpretar el texto del payload.

## Verificación reproducible

Desde `front/`:

```powershell
npm run lint
npm run build
node --experimental-strip-types --test --test-isolation=none tests/sprint3-rules.test.mjs
```

Las cuatro pruebas de reglas verifican estados fallidos/finales, estados desconocidos y los límites de edad, fechas inválidas y años bisiestos.

`tests/sprint3-browser.mjs` es una prueba de navegador por Chrome DevTools Protocol, sin dependencias nuevas. Requiere Vite en `127.0.0.1:5173` con `VITE_API_URL` apuntando a `/api/v1` en ese origen y un Chrome aislado con depuración local en puerto 9227. Ejecutar `node tests/sprint3-browser.mjs` desde `front/`. El script reemplaza las respuestas de API y geolocalización dentro de la página; los paquetes, usuarios, teléfono y firma son datos ficticios. No valida SMTP real ni la precisión del GPS físico.

Se comprobaron a 320 px: escaneo y confirmación separados, selección de sucursal, mapa e historial públicos, visita fallida sin entrega visual, inicio, GPS, contacto ausente, firma y reintento idéntico de entrega, visita fallida y su reintento, permiso GPS denegado, llegada de larga distancia y detención del observador al finalizar, y rechazo de acceso a reparto con rol vendedor. Se capturaron las pantallas en `front/node_modules/.tmp/sprint3-*.png`, incluyendo tema oscuro. La firma generada en navegador se contrasta con el validador PNG del backend.

## Límites de entrega

El frontend de las cuatro historias está implementado. Esto no acredita por sí solo el cierre formal del sprint: quedan aceptación del equipo, validación con GPS físico en HTTPS, configuración real de Mapbox/email y despliegue. La deuda global de Ruff registrada en la auditoría se corrigió posteriormente y el README se limpió conservando los enlaces de ambas versiones, con autorización del usuario. La discrepancia del control de imports permanece como un hallazgo separado.
