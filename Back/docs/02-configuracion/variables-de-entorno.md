# Variables de entorno

Declaradas y validadas en `app/core/config.py` con `pydantic-settings`. Se leen desde un archivo `.env` en `Back/` (ver plantilla en [`Back/.env.example`](../../.env.example)); si una variable no está definida, se usa el valor por defecto del código — por eso el backend puede levantarse en desarrollo sin crear `.env` explícitamente.

| Variable | Default | Descripción |
|---|---|---|
| `PROJECT_NAME` | `Sistema de Gestión de Envíos` | Nombre mostrado en el título de Swagger. |
| `ENVIRONMENT` | `development` | Etiqueta informativa del entorno actual. |
| `DEBUG` | `false` | Activa el echo de SQL de SQLAlchemy. Acepta `true/false`, `1/0`, `yes/no`, `on/off`, `debug/release`, `development/production` (normalizado en `Settings.parse_debug`). |
| `DATABASE_URL` | `sqlite+aiosqlite:///./gestion_envios.db` | Cadena de conexión async de SQLAlchemy. Para Neon: usar el connection string *pooled* del panel de Neon, con el esquema cambiado a `postgresql+asyncpg://` y **sin** el `?sslmode=require` del final (`infrastructure/db/session.py` ya fuerza SSL vía `connect_args`, porque `asyncpg` no entiende ese parámetro en la URL como sí lo hace `psycopg2`). Ver [Plan completo de base de datos](../01-arquitectura/plan-base-de-datos-completo.md#8-aplicar-esto-en-neon). |
| `DATABASE_URL_MIGRACIONES` | vacío | Endpoint con el que Alembic aplica el esquema. Vacío: se usa `DATABASE_URL`, cambiando el host `-pooler` de Neon por el directo. Ver [Mantener Neon actualizada](./base-de-datos-neon.md). |
| `DB_ACTUALIZAR_ESQUEMA_AL_INICIAR` | `true` | Al arrancar, la API aplica `alembic upgrade head` (y adopta bases creadas con `create_all`). |
| `JWT_SECRET` | clave de ejemplo (**cambiar siempre fuera de desarrollo**) | Clave simétrica de firma de los JWT. Mínimo 32 caracteres recomendado. |
| `JWT_ALGORITHM` | `HS256` | Algoritmo de firma usado por `PyJWT`. |
| `JWT_EXPIRATION` | `8h` | Vigencia del token de acceso pleno (`scope=FULL_ACCESS`). Formato aceptado: número + unidad (`s`, `m`, `h`, `d`) o segundos a secas; ver `parse_duration`. |
| `JWT_TEMP_TOKEN_EXPIRATION` | `15m` | Vigencia del token restringido emitido en el primer acceso (`scope=PASSWORD_RESET_ONLY`, HU02). Se mantiene corto a propósito para reducir la ventana de uso indebido. |
| `BCRYPT_SALT_ROUNDS` | `12` | Costo del hash de contraseñas (`infrastructure/auth/hasher.py`). |
| `SUPERADMIN_SEED_PASSWORD` | contraseña de ejemplo | Contraseña en texto plano usada **solo en el seed** para generar el hash del Superadministrador inicial. Si se deja vacía (`None`), el seed de Superadmin se omite (ver log de advertencia al iniciar). |
| `SUPERADMIN_SEED_DNI` | `00000000` | DNI del Superadministrador sembrado. |
| `SUPERADMIN_SEED_EMAIL` | `admin@empresa.com` | Email del Superadministrador sembrado. |
| `SUPERADMIN_SEED_NOMBRE` | `Admin General` | Nombre del Superadministrador sembrado. |
| `SUPERADMIN_SEED_TELEFONO` | `+5493564000000` | Teléfono del Superadministrador sembrado. |
| `FRONTEND_BASE_URL` | `http://localhost:5173` | URL pública del frontend; arma el enlace de seguimiento de los avisos. |
| `EMAIL_PROVIDER` | `mock` | `mock` (solo log), `gmail` (completa `smtp.gmail.com:587`) o `smtp`. Ver [Notificaciones](./notificaciones-email-whatsapp.md). |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USE_TLS` | `localhost` / `587` / `true` | Servidor SMTP. El puerto `465` usa SSL implícito. |
| `SMTP_USER` / `SMTP_PASSWORD` | vacío | Credenciales SMTP. En Gmail, la contraseña de aplicación. |
| `SMTP_FROM_EMAIL` / `SMTP_FROM_NAME` | vacío / `Sistema de Gestión de Envíos` | Remitente. Vacío usa `SMTP_USER`. |
| `SMTP_TIMEOUT_SEGUNDOS` | `15` | Tiempo máximo de conexión SMTP. |
| `WHATSAPP_PROVIDER` | `mock` | `mock`, `twilio`, `meta` o `deshabilitado`. |
| `WHATSAPP_CODIGO_PAIS` | `54` | Código de país asumido para teléfonos sin prefijo internacional. |
| `WHATSAPP_TIMEOUT_SEGUNDOS` | `15` | Tiempo máximo de cada llamada al proveedor. |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` | vacío | Credenciales de Twilio. |
| `TWILIO_WHATSAPP_FROM` | `whatsapp:+14155238886` | Remitente de WhatsApp en Twilio (sandbox por defecto). |
| `TWILIO_CONTENT_SID_NUEVO_ENVIO` / `TWILIO_CONTENT_SID_VISITA_FALLIDA` | vacío | Plantillas aprobadas; vacío envía texto libre (sandbox). |
| `WHATSAPP_META_TOKEN` / `WHATSAPP_META_PHONE_NUMBER_ID` | vacío | Credenciales de WhatsApp Cloud API. |
| `WHATSAPP_META_API_VERSION` | `v21.0` | Versión de la Graph API. |
| `WHATSAPP_META_PLANTILLA_NUEVO_ENVIO` / `WHATSAPP_META_PLANTILLA_VISITA_FALLIDA` | vacío | Nombres de las plantillas aprobadas; vacío envía texto libre (solo dentro de la ventana de 24 h). |
| `WHATSAPP_META_IDIOMA_PLANTILLA` | `es_AR` | Idioma con el que se aprobaron las plantillas. |

## Reglas para el equipo

- Los valores de `SUPERADMIN_SEED_*` y `JWT_SECRET` de este documento y de `.env.example` son **solo para desarrollo local**. No deben reutilizarse en ningún ambiente compartido (staging, producción) ni en la defensa/demo del proyecto si esa demo queda expuesta públicamente.
- Nunca commitear un archivo `.env` con valores reales — está en `.gitignore`; solo `.env.example` (sin secretos reales) va al repositorio.
- Si se agrega una variable nueva a `Settings`, actualizar en el mismo cambio: esta tabla, `.env.example` y, si aplica, `Back/README.md`.