# Backend de Gestión de Envíos

API construida con FastAPI y Python 3.12 o superior. Para desarrollo local utiliza SQLite, por lo que no requiere instalar ni levantar un servidor de base de datos.

## Preparación inicial en Windows

Desde la carpeta `Back`:

```powershell
py -3.12 -m venv .venv
Copy-Item .env.example .env
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Si `.venv` ya existe, solamente es necesario ejecutar la instalación de dependencias.

## Iniciar la API

```powershell
& .\.venv\Scripts\python.exe run.py
```

El servidor queda disponible en:

- API: `http://localhost:8000`
- Health check: `http://localhost:8000/health`
- Swagger: `http://localhost:8000/docs`

Al iniciar, la API aplica las migraciones de Alembic pendientes (también contra Neon) y siembra los roles base, las sucursales y el superadministrador configurado en `.env`. Ver [Mantener Neon actualizada](docs/02-configuracion/base-de-datos-neon.md).

Para actualizar o verificar una base sin levantar la API:

```powershell
& .\.venv\Scripts\python.exe -m app.infrastructure.db.actualizar_base --verificar
& .\.venv\Scripts\python.exe -m app.infrastructure.db.actualizar_base
```

## Notificaciones

Por defecto los avisos de email y WhatsApp solo se registran en el log (`mock`). Para enviarlos con Gmail y Twilio o Meta, seguir [Notificaciones por email y WhatsApp](docs/02-configuracion/notificaciones-email-whatsapp.md).

Credenciales del ejemplo exclusivamente para desarrollo local:

- DNI: `00000000`
- Contraseña: `SuperAdmin2026!*`

No reutilizar estos valores en otros ambientes.

## Verificaciones

```powershell
& .\.venv\Scripts\python.exe -m pip check
& .\.venv\Scripts\python.exe -m pytest -q
```

Para revisar estilo y modernización del código:

```powershell
& .\.venv\Scripts\python.exe -m ruff check .
```

## Integración con el frontend

La API monta sus endpoints bajo `/api/v1`. Para que el frontend forme la URL final `/api/v1/auth/login`, su variable debe apuntar a:

```dotenv
VITE_API_URL=http://localhost:8000/api/v1
```

El login actual del backend recibe un JSON con `dni` y `password`.
