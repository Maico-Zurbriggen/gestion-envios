# Mantener Neon actualizada

**Neon es solo la base de producción**: la usa la app publicada en el VPS ([Despliegue en el VPS](./despliegue-vps.md)). El desarrollo local usa SQLite (`DATABASE_URL=sqlite+aiosqlite:///./gestion_envios.db`), así las pruebas no tocan los datos publicados ni mandan avisos a sus clientes. No conectar el entorno local a Neon.

Neon antes quedaba desactualizada después de cada cambio de modelo porque la API creaba las tablas con `Base.metadata.create_all` al arrancar. `create_all` crea tablas que faltan pero **nunca agrega columnas ni restricciones** a tablas existentes y no registra la versión en `alembic_version`, así que después tampoco se podía correr `alembic upgrade head`.

Desde ahora el esquema solo cambia con migraciones de Alembic y se aplican solas en tres momentos.

## 1. Al arrancar la API

`ejecutar_siembra()` llama a `actualizar_esquema_al_iniciar()` (`app/infrastructure/db/actualizar_base.py`), que corre `alembic upgrade head` contra la base de `DATABASE_URL`:

- Si la base ya está al día, no hace nada: el log dice `Esquema de … al día (revisión …)`.
- Si faltan migraciones, las aplica y lo informa.
- Si la base fue creada con `create_all` (no tiene `alembic_version`), detecta en qué revisión está, la marca y migra desde ahí.
- En PostgreSQL toma un candado asesor (`pg_advisory_xact_lock`): si dos personas arrancan la API a la vez contra Neon, la segunda espera y encuentra la base ya migrada.
- Si Neon está en una revisión **más nueva** que tu código (otra persona ya subió una migración que vos no tenés), la API arranca igual y el log pide `git pull`.

Se desactiva con `DB_ACTUALIZAR_ESQUEMA_AL_INICIAR=false`.

## 2. En cada push a `development` o `main`

El workflow `.github/workflows/ci-neon.yml` corre lint, build y pruebas de front y back. Si pasan, aplica las migraciones a Neon. Hay que cargar una vez el secreto del repositorio **`NEON_DATABASE_URL`** (GitHub → Settings → Secrets and variables → Actions → New repository secret) con el connection string que copia el panel de Neon. Sin el secreto, el paso se omite con una advertencia.

## 3. A mano, cuando haga falta

Desde `Back/`:

```powershell
# Estado: revisión actual, pendientes y diferencias con los modelos. No modifica nada.
& .\.venv\Scripts\python.exe -m app.infrastructure.db.actualizar_base --verificar

# Aplicar lo pendiente a la base del .env
& .\.venv\Scripts\python.exe -m app.infrastructure.db.actualizar_base

# Contra otra base, pegando el connection string tal como lo da Neon, y cargando datos base
& .\.venv\Scripts\python.exe -m app.infrastructure.db.actualizar_base --database-url "postgresql://usuario:clave@ep-xxxx-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require" --semillas
```

Código de salida: `0` si la base quedó en la última revisión, `1` si quedan pendientes (con `--verificar`), `2` ante un error.

## Connection strings de Neon

Se puede pegar el connection string del panel sin editarlo: `postgresql://` pasa a `postgresql+asyncpg://` y se quitan `sslmode` y `channel_binding` (el SSL se fuerza por código). Las migraciones usan el **endpoint directo** (Neon recomienda no hacer DDL a través del pooler): si `DATABASE_URL` apunta al host `-pooler`, se deriva el directo quitando `-pooler`. Para usar otro, configurar `DATABASE_URL_MIGRACIONES`.

## Cómo cambiar el esquema a partir de ahora

1. Modificar `app/infrastructure/db/models.py`.
2. Generar la migración y **revisarla** antes de subirla:

   ```powershell
   & .\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "descripcion del cambio"
   ```

   En SQLite los cambios sobre tablas existentes deben usar `op.batch_alter_table`, como las migraciones existentes.
3. Correr `pytest`. `tests/integration/test_actualizar_base.py::test_los_modelos_no_tienen_cambios_sin_migracion` falla si un cambio de modelo no tiene migración: es la protección para que Neon no vuelva a quedar atrás.
4. Al hacer merge a `development`, el workflow aplica la migración en Neon. Quien arranque la API con el código nuevo también la aplica.

No volver a usar `create_all` para cambios nuevos ni editar migraciones ya aplicadas en Neon: crear una nueva.
