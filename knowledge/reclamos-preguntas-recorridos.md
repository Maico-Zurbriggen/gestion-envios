# Reclamos, preguntas frecuentes y recorridos (HU07 / HU08 / HU10)

Resumen de los contratos del backend. El detalle completo (requests, respuestas y errores) está en [`Back/Contrato/endpoints_frontend.md`](../Back/Contrato/endpoints_frontend.md), secciones 11 a 13, y las decisiones de implementación en `Back/docs/04-historias-de-usuario/`. Todo verificable en Swagger (`/docs`).

## Reclamos desde la vista pública (HU07)

- Público, con el mismo token de seguimiento de HU04 (se acepta en minúsculas o con espacios).
- `GET /api/v1/reclamos/seguimiento/{token}`: habilita el formulario. Devuelve `puede_iniciar`, `tipos_reclamo` (código + descripción para mostrar), `paquetes` del envío y `reclamos` ya iniciados con estado y resolución.
- `POST /api/v1/reclamos/seguimiento/{token}`: `tipo` (`DEMORA`, `DANIO`, `EXTRAVIO`, `OTRO`), `descripcion` (20–2000), `numero_paquete` opcional, `contacto_nombre` y **al menos uno** de `contacto_email` / `contacto_telefono`. `409` si ya hay un reclamo igual en curso.
- La parte pública no expone datos de contacto.
- Gestión interna en `/api/v1/admin/reclamos` (`ADMINISTRATIVO`, `SUPERADMIN`): bandeja con filtros y cambio de estado. Cerrar (`RESUELTO`/`RECHAZADO`) exige `resolucion`, que se muestra en la vista pública.

### Frontend público de HU07

- En `/seguimiento`, después de consultar un envío válido, `Iniciar reclamo` abre el formulario en la misma pantalla y carga el contexto desde la API. No requiere sesión ni una ruta adicional.
- La feature `front/src/features/claims/` mantiene componentes, tipos, servicios y hooks de TanStack Query. El formulario permite elegir el envío completo o uno de sus paquetes, y valida descripción, nombre y al menos un medio de contacto.
- El panel muestra confirmación, reclamos anteriores, estado y resolución pública. Actualiza el historial después de crear, ante un duplicado y por acción del usuario; respeta `puede_iniciar` y el motivo de inhabilitación del servidor.
- Cambiar el envío consultado reinicia el panel y su formulario. Los datos de contacto no se conservan después de un alta exitosa ni se agregan al historial público.
- Este alcance cubre el inicio público previsto en la pila del Sprint 3. La bandeja de gestión interna todavía no tiene interfaz en el frontend.

## Preguntas frecuentes (HU08)

- Público: `GET /api/v1/preguntas-frecuentes?categoria=&q=`. Los filtros ignoran mayúsculas y tildes.
- Respuesta: `total`, `categorias` (siempre todas, con su cantidad, para armar los filtros) y `preguntas` ya ordenadas. La categoría nunca viene vacía (`"General"`).
- El contenido vive en base y se administra en `/api/v1/admin/preguntas-frecuentes` (`ADMINISTRATIVO`, `SUPERADMIN`); el frontend no debe hardcodear preguntas. Al arrancar el backend se siembran 13 preguntas iniciales si la tabla está vacía.

### Frontend público de HU08

- `/preguntas-frecuentes` se declara en `AuthRoutes.tsx` y no requiere sesión. Tiene accesos desde el login, el seguimiento y el registro público; este último abre la ayuda en otra pestaña para conservar el formulario del envío.
- La feature `front/src/features/faq/` consulta el contenido mediante TanStack Query y transforma los contratos de API a modelos de la interfaz. Las preguntas, respuestas, categorías, cantidades y orden provienen del backend.
- La búsqueda y el filtro por tema se envían a la API y quedan en la URL (`q`, `categoria`) para compartir consultas y conservarlas al recargar o navegar atrás. Las respuestas se despliegan con controles nativos accesibles por teclado; al buscar, los resultados se muestran abiertos.
- La API busca coincidencias literales: `peso` no coincide con `pesar`. Si la consulta no tiene resultados, el servicio del frontend reintenta `peso`/`pesos` como `pesar`, manteniendo los demás términos y la categoría. Las coincidencias literales tienen prioridad y el contenido sigue viniendo de la API.
- Incluye carga, reintento, búsqueda sin coincidencias y sección sin contenido publicado, con temas claro y oscuro y diseño desde 320 px. El alcance es la consulta pública de HU08; la administración de contenido no tiene interfaz en el frontend.

## Recorridos de reparto (HU10)

Todo requiere `ADMINISTRATIVO` o `SUPERADMIN`.

1. **Perfil de repartidor** (una vez por repartidor): `PUT /api/v1/repartidores/{usuario_id}/perfil` con `sucursal_base_id`, `tipo_reparto` (`CORTA` | `LARGA`) y `activo`. Sin perfil, un usuario REPARTIDOR no recibe recorridos.
2. **Qué espera recorrido**:
   - `GET /api/v1/recorridos/pendientes/resumen`: registrados que todavía no llegaron a una sucursal (`sin_llegar`) y, por sucursal, cuántos esperan un recorrido `a_domicilio` o `entre_sucursales`.
   - `GET /api/v1/recorridos/pendientes?sucursal_id=&tipo_distancia=`: los paquetes de una sucursal, con destino, si tienen ubicación y el `motivo` si no se pueden planificar.
3. **Armar a mano**: `POST /api/v1/recorridos` con `sucursal_id`, `tipo_distancia`, `fecha`, `repartidor_id` (libre ese día) y `paquetes` (códigos en orden). Queda `EN_EDICION`.
4. **Armar automáticamente**: `POST /api/v1/recorridos/generar` con `sucursal_id`, `tipo_distancia` y opcionales `fecha` y `repartidor_ids`. Reparte por zonas solo lo que espera recorrido, entre los repartidores libres, y optimiza el orden. **Lo ya armado se respeta.** Con `reemplazar_existentes: true` descarta los recorridos sin iniciar y vuelve a repartir todo. `orientacion_calles_grados` es opcional (0 por defecto). Devuelve `resumen`, `recorridos` y `alertas`.
5. **Visualizar**: `GET /api/v1/recorridos?desde=&hasta=` (una semana) y `GET /api/v1/recorridos/{id}` trae `paradas` en orden (con coordenadas y paquetes) y `trazado` (puntos de las paradas en orden; el recorrido por calles lo da `POST /api/v1/mapa/trayecto`).
6. **Editar** (solo `GENERADO`/`EN_EDICION`): `PUT /{id}/paquetes` con la lista completa en orden, `DELETE /{id}/paquetes/{codigo}`, `POST /{id}/optimizar`, `PATCH /{id}/repartidor`, `DELETE /{id}`. Cada respuesta trae las `alertas` vigentes.
7. **Iniciar**: `POST /{id}/iniciar` (desde `GENERADO` o `EN_EDICION`; normalmente lo hace el repartidor desde su app). Los paquetes pasan a `EN_REPARTO` (corta) o `EN_TRANSITO` (larga) y el seguimiento público lo refleja.
8. **Alertas** de paquetes sin recorrido: `GET /api/v1/recorridos/alertas?sucursal_id=`. Se resuelven solas cuando el paquete entra en un recorrido; la trazabilidad del monitor las muestra.

**Corta / larga distancia:** corta = entregas a domicilio que atiende la propia sucursal (paradas `DOMICILIO`, vuelve a la sucursal); larga = traslados a otra sucursal (paradas `SUCURSAL`, termina en la última).

**Domicilios sin coordenadas** (registrados sin marcar el mapa): no entran en la generación automática y se alertan; se pueden agregar a mano a un recorrido y aparecen como parada con `latitud: null`.

Para completar un domicilio ya agregado, `PATCH /api/v1/recorridos/{id}/paquetes/{codigo}/ubicacion` recibe `{ "latitud", "longitud" }`. Requiere un recorrido de corta distancia sin iniciar y un domicilio sin coordenadas. Guarda el punto en el envío, compartido por todos sus paquetes, y recalcula las estimaciones de sus recorridos activos editables sin cambiar el orden. Rechaza la operación si alguno está en curso o si el punto cambia la sucursal que debe atender un recorrido asignado.

Los paquetes solo entran en un recorrido después de recibirse en la terminal (HU06): un paquete `Pendiente` todavía no está en la sucursal.

### Frontend de HU10

Pantalla `/recorridos` (módulo «Recorridos»), al estilo de las hojas de ruta de Aviso Entrega:

- **Circuito en tres pasos**, con números reales:
  1. registrados sin llegar, con acceso a «Recibir paquetes»;
  2. en sucursal esperando recorrido, por sucursal y tipo (un clic elige esa sucursal y pestaña);
  3. en recorrido ese día.

  Si en el equipo nunca se eligió una sucursal, se propone la que tiene más paquetes esperando.
- **Sucursal** (se recuerda en el equipo, `recorridos-sucursal`), **tipo** («A domicilio» o «Entre sucursales») y **semana** con el resumen de cada día. El día es el de salida de los recorridos: los paquetes en espera no tienen fecha. El día, el tipo y el recorrido abierto quedan en la URL.
- **Indicadores del día** y una **tarjeta por recorrido** con su avance (entregados, sin entregar y pendientes).
- **Nuevo recorrido:** día de salida, repartidor libre y paquetes en espera para elegir con un clic (búsqueda y filtro por ubicación).
- **Armar automáticamente:** muestra cuántos esperan, deja elegir los repartidores (los ocupados ese día aparecen deshabilitados) y al terminar lista los recorridos armados y lo que quedó esperando, con el motivo.
- **Repartidores:** botón del encabezado que abre la configuración de perfiles.
- **Espacio de trabajo de un recorrido:**
  - encabezado con métricas e «Iniciar recorrido», «Cambiar repartidor» y «Eliminar»;
  - lista «Antes de salir»: repartidor, paquetes y ubicaciones;
  - paradas que se reordenan arrastrando o con flechas, y se guardan solas;
  - quitar un paquete lo devuelve a la espera; «Optimizar» ordena el recorrido;
  - a la derecha, el mapa, el panel «Agregar» con los paquetes en espera, o «Ubicar domicilio» para paradas sin coordenadas.

  Un recorrido en reparto o finalizado es de consulta y se actualiza cada 30 segundos.
- El trayecto por calles usa [OSRM](./mapas.md) por calles y rutas, sin diagonales; el orden de las paradas sale de los tiempos reales de manejo.
- Los estilos base (botones, avisos, mapa) están en `features/routes/routes.css` y los importa cada componente; la app del repartidor reutiliza el mapa sin cargar la página de recorridos.
