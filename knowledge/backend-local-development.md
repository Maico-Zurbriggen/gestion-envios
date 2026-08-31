# Desarrollo local del backend

El backend utiliza Python 3.12 o superior y FastAPI. Las dependencias se declaran en `Back/requirements.txt` y se instalan en `Back/.venv`.

Para desarrollo local se eligió SQLite mediante `sqlite+aiosqlite:///./gestion_envios.db`. Esto permite iniciar la API sin infraestructura adicional. PostgreSQL podrá configurarse más adelante reemplazando `DATABASE_URL`.

El proceso de inicio crea las tablas, siembra los roles base y crea el superadministrador cuando todavía no existe. Las variables y credenciales de ejemplo están documentadas en `Back/.env.example` y no deben reutilizarse fuera del entorno local.

Comando de inicio:

```powershell
& .\.venv\Scripts\python.exe run.py
```

La API escucha en el puerto `8000`, expone `/health` y publica Swagger en `/docs`. Los endpoints funcionales se montan bajo `/api/v1`.
