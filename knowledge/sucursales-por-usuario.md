# Sucursales por usuario: todo se divide por sucursal

Tomado de Aviso Entrega Clientes (`SucursalAcceso`, `ElegirSucursalPage`, `SucursalSwitcher`) y adaptado a este sistema.

## Quién entra en qué sucursal

| Rol | Sucursales | Al ingresar |
|---|---|---|
| Superadministrador | Todas, también las inactivas. | Elige una si hay más de una. |
| Administrativo y vendedor | Solo las habilitadas en Usuarios y que estén activas. Necesitan al menos una. | Con una sola entra directo; con más, elige en `/elegir-sucursal`. |
| Repartidor | Una sola: la que se le asigna en Usuarios, que es también su sucursal base de reparto. | No elige: sale siempre de su base. |

- En Usuarios, el campo «¿A qué sucursal pertenece?» está siempre a la vista: varias para vendedor y administrativo, una sola para repartidor, ninguna para el Superadministrador (no guarda sucursales). Sin completarlo no se puede guardar, y el backend también lo exige (`requiere_sucursales`, `una_sola_sucursal`).
- Al cambiar de rol se vuelven a validar las sucursales: por ejemplo, un vendedor con dos sucursales no pasa a repartidor sin elegir una.
- La sucursal del repartidor y su base de reparto están sincronizadas en los dos sentidos. Si se cambia en Usuarios, se mueve su perfil de reparto; si se cambia la base en Recorridos › Repartidores, cambia su sucursal. Con recorridos activos no se puede cambiar (409).

- La tabla `usuario_sucursales` guarda las sucursales habilitadas. La migración `e5b19c3a7d20` habilita todas las sucursales a los administrativos y vendedores que ya existían, y su sucursal base a los repartidores, para no dejar a nadie sin acceso.
- `sucursales.activa`: una sucursal inactiva no se ofrece para envíos nuevos ni puede elegirse, salvo el Superadministrador.
- El login y `/auth/me` devuelven `user.sucursales`, que son las que puede elegir. Las reglas están en `domain/rules/sucursal_rules.py`.

## La sucursal activa

- En el frontend, `activeBranchId` vive en Redux (`authSlice`) y se recuerda por usuario en `localStorage` (`gestion-envios.active-branch`). Se cambia desde el menú de la barra superior (`BranchSwitcher`): un menú propio, accesible con teclado (flechas, Inicio, Fin, Enter, Escape), con la ciudad de cada sucursal y un tilde en la activa.
- `ProtectedRoutes` manda a `/elegir-sucursal` a quien necesita sucursal y no tiene una activa. El envoltorio general solo exige sesión (`requireBranch={false}`), porque si no la pantalla de elegir se redirige a sí misma.
- Las pantallas usan `useActiveBranch()` y ya no tienen selectores propios: Recibir paquetes, Carga y descarga, Registrar retiro, Recorridos, Monitor, Reclamos y el registro de envíos en el mostrador.

## El backend verifica la sucursal

En vez de un header como `X-Sucursal`, cada endpoint recibe `sucursal_id` y lo verifica (`api/dependencies.py`):

- `verificar_sucursal(usuario, id)` devuelve 403 si el usuario no tiene habilitada esa sucursal. La usan admisión, retiro, carga y descarga, recorridos (incluidos los que operan por `id` de recorrido) y repartidores.
- `exigir_sucursal(usuario, id)`: en los listados, quien no entra en todas tiene que indicar la sucursal (400). La usan el monitor (resumen, listado y exportación), las alertas y listados de recorridos y la bandeja de reclamos.
- `sucursales_habilitadas(usuario)` devuelve `None` para el Superadministrador, que entra en todas.

## Cada envío tiene sucursal de origen

- `POST /envios` exige `sucursal_origen_id`: en el formulario público, «¿A qué sucursal lo vas a llevar?»; en el mostrador, la sucursal activa. Se guarda en `paquetes.sucursal_origen_id` desde el registro y la admisión la corrige si el cliente lo lleva a otra.
- «Registrados sin llegar» se cuenta por esa sucursal (`EsperaSucursalData.sin_llegar`).
- El monitor considera que un paquete pertenece a una sucursal si la tiene como origen, si está en ella o si se retira ahí.
- Los paquetes registrados antes de este cambio no tienen origen hasta que se admiten.

## Administración de sucursales

`GET`, `POST` y `PUT /admin/sucursales` (solo Superadministrador), en la pantalla Administración › Sucursales:

- Nombre, provincia, ciudad, dirección y ubicación (latitud y longitud) son obligatorios, porque la dirección es el punto de partida de los recorridos. Se ubica con Georef (Ubicar en el mapa) y se ajusta arrastrando el marcador.
- El nombre no se repite (409).
- Al guardar, se refresca la sesión para que el selector de arriba muestre los cambios.
