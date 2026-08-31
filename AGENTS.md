# Gestión de envíos

## Alcance actual

- El frontend vive en `front/` y utiliza React, TypeScript y Vite.
- El backend vive en `Back/` y utiliza Python 3.12+, FastAPI y SQLAlchemy async.
- Antes de modificar una decisión transversal, consultar los documentos de `knowledge/`.
- Ejecutar los comandos de Node desde `front/`.
- Ejecutar los comandos Python desde `Back/` con `.venv/Scripts/python.exe`.

## Arquitectura del frontend

- Organizar cada dominio dentro de `src/features/<feature>/`.
- Mantener páginas, hooks, servicios, estado y tipos dentro de su feature cuando sean específicos del dominio.
- Usar Redux Toolkit para estado global del cliente y TanStack Query para operaciones remotas.
- No duplicar respuestas remotas completas en Redux. Guardar allí solamente estado global necesario entre pantallas, como la sesión.
- Centralizar las rutas públicas en `AuthRoutes.tsx` y las privadas en `MainRoutes.tsx`.
- Toda ruta privada debe quedar bajo `ProtectedRoutes.tsx`.
- Mantener el acceso HTTP fuera de los componentes visuales.

## API y modelos

- Construir las URLs desde `VITE_API_URL`; no escribir hosts directamente en el código.
- Tipar tanto las respuestas exitosas como los errores esperados.
- Conservar snake_case solamente en los contratos de API y mapearlo a camelCase para el resto de la aplicación.
- Mostrar mensajes de error comprensibles y no exponer detalles internos del servidor.

## Identidad visual y accesibilidad

- Reutilizar los tokens de `front/src/styles/theme.css`.
- Usar iconos de `lucide-react`, especialmente en botones y acciones; no incorporar otra librería de iconos sin una razón documentada.
- No agregar colores hexadecimales en componentes si existe un token equivalente.
- Mantener foco visible, labels asociados a controles, estados de carga y mensajes accesibles.
- Las vistas deben funcionar como mínimo desde 320 px de ancho.

## Verificación

- Antes de entregar cambios, ejecutar `npm run lint` y `npm run build`.
- Para cambios en el backend, ejecutar `python -m pip check` y `python -m pytest -q` dentro de su entorno virtual.
- No modificar archivos `.env` ni incluir credenciales en el repositorio.
