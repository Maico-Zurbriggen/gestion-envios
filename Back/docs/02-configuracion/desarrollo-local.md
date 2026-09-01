# Desarrollo local

Ampliación de lo que ya resume [`Back/README.md`](../../README.md) y [`knowledge/backend-local-development.md`](../../../knowledge/backend-local-development.md), con el detalle de qué pasa puertas adentro al levantar la API.

## Puesta en marcha

```powershell
py -3.12 -m venv .venv
Copy-Item .env.example .env
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe run.py
```

`run.py` arranca Uvicorn apuntando a `app.api.main:app` en el puerto `8000`, con recarga automática ante cambios de código.

## Qué pasa en el primer arranque

El `lifespan` de `crear_aplicacion()` (`app/api/main.py`) ejecuta, en orden, `ejecutar_siembra()` (`app/infrastructure/db/seed.py`):

1. `crear_tablas()` — crea todas las tablas del modelo si no existen (`Base.metadata.create_all`, ver la nota sobre Alembic en [Modelo de datos](../01-arquitectura/modelo-de-datos.md)).
2. `sembrar_roles()` — inserta los 4 roles base si no existen.
3. `sembrar_superadmin()` — si `SUPERADMIN_SEED_PASSWORD` está definida y no existe ya un usuario con ese DNI/email, crea el Superadministrador con `requiere_cambio_password=False`.
4. `sembrar_sucursales()` — inserta las 6 sucursales de ejemplo si no existen (matching por nombre).

Todo esto es idempotente: reiniciar el servidor no duplica datos, cada función chequea existencia antes de insertar.

## Endpoints útiles para verificar que todo funciona

| Verificación | Comando |
|---|---|
| El servidor responde | `curl http://localhost:8000/health` |
| Los endpoints están montados | Abrir `http://localhost:8000/docs` (Swagger) o `http://localhost:8000/openapi.json` |
| Login del Superadmin sembrado | `POST /api/v1/auth/login` con el DNI/contraseña de `SUPERADMIN_SEED_*` |
| Catálogo de sucursales | `GET /api/v1/sucursales` |

## Reiniciar desde cero

Si se quiere volver a un estado limpio en desarrollo, alcanza con borrar el archivo SQLite (`gestion_envios.db`, en `.gitignore`) y reiniciar el servidor — se vuelve a crear y sembrar automáticamente.

## Verificaciones antes de subir cambios

Según [`AGENTS.md`](../../../AGENTS.md), antes de entregar cualquier cambio de backend:

```powershell
& .\.venv\Scripts\python.exe -m pip check
& .\.venv\Scripts\python.exe -m pytest -q
```

Y opcionalmente lint:

```powershell
& .\.venv\Scripts\python.exe -m ruff check .
```