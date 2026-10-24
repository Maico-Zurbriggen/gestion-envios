# Reclamos, preguntas frecuentes y recorridos (HU07 / HU08 / HU10)

Resumen de los contratos del backend. El detalle completo (requests, respuestas y errores) está en [`Back/Contrato/endpoints_frontend.md`](../Back/Contrato/endpoints_frontend.md), secciones 11 a 13, y las decisiones de implementación en `Back/docs/04-historias-de-usuario/`. Todo verificable en Swagger (`/docs`).

## Reclamos desde la vista pública (HU07)

- Público, con el mismo token de seguimiento de HU04 (se acepta en minúsculas o con espacios).
- `GET /api/v1/reclamos/seguimiento/{token}`: habilita el formulario. Devuelve `puede_iniciar`, `tipos_reclamo` (código + descripción para mostrar), `paquetes` del envío y `reclamos` ya iniciados con estado y resolución.
- `POST /api/v1/reclamos/seguimiento/{token}`: `tipo` (`DEMORA`, `DANIO`, `EXTRAVIO`, `OTRO`), `descripcion` (20–2000), `numero_paquete` opcional, `contacto_nombre` y **al menos uno** de `contacto_email` / `contacto_telefono`. `409` si ya hay un reclamo igual en curso.
- La parte pública no expone datos de contacto.
- Gestión interna en `/api/v1/admin/reclamos` (`ADMINISTRATIVO`, `SUPERADMIN`): bandeja con filtros y cambio de estado. Cerrar (`RESUELTO`/`RECHAZADO`) exige `resolucion`, que se muestra en la vista pública.

## Preguntas frecuentes (HU08)

- Público: `GET /api/v1/preguntas-frecuentes?categoria=&q=`. Los filtros ignoran mayúsculas y tildes.
- Respuesta: `total`, `categorias` (siempre todas, con su cantidad, para armar los filtros) y `preguntas` ya ordenadas. La categoría nunca viene vacía (`"General"`).
- El contenido vive en base y se administra en `/api/v1/admin/preguntas-frecuentes` (`ADMINISTRATIVO`, `SUPERADMIN`); el frontend no debe hardcodear preguntas. Al arrancar el backend se siembran 13 preguntas iniciales si la tabla está vacía.

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

Los paquetes solo entran en un recorrido después de recibirse en la terminal (HU06): un paquete `Pendiente` todavía no está en la sucursal.
