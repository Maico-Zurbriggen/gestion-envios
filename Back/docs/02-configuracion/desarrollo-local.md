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

1. `actualizar_esquema_al_iniciar()` — aplica las migraciones de Alembic pendientes (`alembic upgrade head`). Una base vacía se crea completa; una creada antes con `create_all` se adopta y se migra. Ver [Mantener Neon actualizada](./base-de-datos-neon.md).
2. `sembrar_roles()` — inserta los 4 roles base si no existen.
3. `sembrar_superadmin()` — si `SUPERADMIN_SEED_PASSWORD` está definida y no existe ya un usuario con ese DNI/email, crea el Superadministrador con `requiere_cambio_password=False`.
4. `sembrar_sucursales()` — inserta las 6 sucursales de ejemplo si no existen (matching por nombre).
5. `sembrar_preguntas_frecuentes()` — carga las 13 preguntas frecuentes iniciales (HU08) **solo si la tabla está vacía**, para no volver a crear contenido que un administrador borró o editó.

Todo esto es idempotente: reiniciar el servidor no duplica datos, cada función chequea existencia antes de insertar.

## Bases creadas antes con `create_all`

Ya no hace falta borrar `gestion_envios.db` ni correr `alembic stamp` a mano: al arrancar, la API detecta una base sin `alembic_version`, la marca en la revisión que corresponde y aplica las migraciones que falten. Lo mismo hace `python -m app.infrastructure.db.actualizar_base`.

## Endpoints útiles para verificar que todo funciona

| Verificación | Comando |
|---|---|
| El servidor responde | `curl http://localhost:8000/health` |
| Los endpoints están montados | Abrir `http://localhost:8000/docs` (Swagger) o `http://localhost:8000/openapi.json` |
| Login del Superadmin sembrado | `POST /api/v1/auth/login` con el DNI/contraseña de `SUPERADMIN_SEED_*` |
| Catálogo de sucursales | `GET /api/v1/sucursales` |
| Preguntas frecuentes sembradas | `GET /api/v1/preguntas-frecuentes` |

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