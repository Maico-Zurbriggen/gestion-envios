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
2. **Generar**: `POST /api/v1/recorridos/generar` con `sucursal_id`, `tipo_distancia`, y opcionales `fecha`, `orientacion_calles_grados` (0 a <90), `repartidor_ids`, `reemplazar_existentes`. Reparte de forma equitativa por zonas y optimiza el orden. Devuelve `resumen`, `recorridos` y `alertas`.
3. **Visualizar**: `GET /api/v1/recorridos/{id}` trae `paradas` en orden (con coordenadas y paquetes) y `trazado` (polilínea lista para Leaflet).
4. **Editar** (solo `GENERADO`/`EN_EDICION`): `PUT /{id}/paquetes` con la lista completa en orden, `DELETE /{id}/paquetes/{codigo}`, `POST /{id}/optimizar`, `PATCH /{id}/repartidor`, `DELETE /{id}`. Cada respuesta trae las `alertas` vigentes.
5. **Iniciar**: `POST /{id}/iniciar`. Los paquetes pasan a `EN_REPARTO` (corta) o `EN_TRANSITO` (larga) y el seguimiento público lo refleja.
6. **Alertas** de paquetes sin recorrido: `GET /api/v1/recorridos/alertas?sucursal_id=`; mostrar `descripcion_motivo`.

**Corta / larga distancia:** corta = entregas a domicilio que atiende la propia sucursal (paradas `DOMICILIO`, vuelve a la sucursal); larga = traslados a otra sucursal (paradas `SUCURSAL`, termina en la última).

**Domicilios sin coordenadas** (registrados sin marcar el mapa): no entran en la generación automática y se alertan; se pueden agregar a mano a un recorrido y aparecen como parada con `latitud: null`.

Para completar un domicilio ya agregado, `PATCH /api/v1/recorridos/{id}/paquetes/{codigo}/ubicacion` recibe `{ "latitud", "longitud" }`. Requiere un recorrido de corta distancia sin iniciar y un domicilio sin coordenadas. Guarda el punto en el envío, compartido por todos sus paquetes, y recalcula las estimaciones de sus recorridos activos editables sin cambiar el orden. Rechaza la operación si alguno está en curso o si el punto cambia la sucursal que debe atender un recorrido asignado.

Los paquetes solo entran en un recorrido después de recibirse en la terminal (HU06): un paquete `Pendiente` todavía no está en la sucursal.

### Frontend de HU10

- `/recorridos` está bajo las rutas privadas de `MainRoutes.tsx`, con roles `ADMINISTRATIVO` y `SUPERADMIN`. La navegación y el Home muestran el acceso desde `app/navigation.ts`.
- La feature `front/src/features/routes/` mantiene contratos, modelos camelCase, servicios, hooks y componentes. TanStack Query conserva las consultas y actualiza recorridos y alertas después de las operaciones; Redux solo aporta la sesión.
- Permite configurar perfiles de repartidor, filtrar por sucursal/fecha/tipo, generar con orientación y selección opcional de repartidores, y reemplazar planificaciones sin iniciar con confirmación explícita. El listado admite filtros adicionales por estado y repartidor.
- El detalle usa Leaflet y [Mapbox Directions](./mapbox-routing.md) para dibujar los trayectos siguiendo calles y carreteras, numerar paradas y señalar la sucursal inicial. Mapbox conserva el orden de las paradas; el backend sigue asignando paquetes y optimizando su orden. Las paradas sin coordenadas se listan y se advierten, sin inventar su ubicación.
- La edición permite reordenar con botones de teclado, agregar y quitar paquetes, optimizar y reasignar repartidor. El borrador se conserva ante errores y bloquea los cambios de contexto hasta guardarlo o cancelarlo. Para mover paquetes entre recorridos se quitan y guardan en el origen y se agregan por código al destino.
- Las paradas de domicilio sin coordenadas ofrecen **Ubicar domicilio** antes de iniciar. Permite seleccionar el punto en un mapa centrado inicialmente en la sucursal (sin asumir que ese sea el destino) o ingresar latitud y longitud por teclado. Guardar persiste la ubicación, actualiza las consultas de recorridos y solicita el trayecto por calles con las nuevas coordenadas. Cancelar no modifica los datos y un error conserva el punto ingresado.
- Iniciar y eliminar requieren confirmación. Un recorrido en curso o finalizado es de consulta. Si su estado cambia durante una edición, se ofrece salir del borrador sin intentar guardar sobre un recorrido bloqueado.
- Las alertas muestran el motivo del servidor, permiten copiar el código, consultar el seguimiento y marcar un caso atendido por fuera del sistema. Su alcance es la sucursal seleccionada para ambos tipos de reparto, independiente de la fecha del listado.
