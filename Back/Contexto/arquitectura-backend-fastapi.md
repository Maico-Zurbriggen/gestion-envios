# Arquitectura del backend — Guía del proyecto

Este backend usa **Python 3.12+ y FastAPI**, siguiendo una Clean Architecture
adaptada a Python (equivalente al patrón usado en TamboBI/.NET, pero sin la
separación en múltiples proyectos/DLLs — acá son capas por *paquete* dentro
de un único proyecto Python).

## 1. Estructura de carpetas

```text
app/
├── api/                      # Capa de presentación: routers, dependencias HTTP, middlewares
│   └── v1/
│       └── routers/          # Un router por recurso (ej. animales.py, auth.py)
│   ├── dependencies.py       # Depends() reutilizables (auth, permisos, paginación)
│   ├── middleware.py         # Manejo de errores, correlation id, compresión
│   └── main.py                # Arranque de la app, wiring de todo
├── application/               # Casos de uso: orquestan domain + infrastructure
│   ├── interfaces/            # Protocols (equivalente a las interfaces IServicioX)
│   └── services/               # Implementación de casos de uso
├── domain/                    # Entidades, reglas de negocio puras, constantes
│   ├── entities/
│   ├── constants/              # Permisos, roles, códigos de error
│   └── rules/                  # Lógica de cálculo sin I/O (equivalente a Domain/Analytics)
├── infrastructure/             # Implementaciones concretas: DB, auth, servicios externos
│   ├── db/
│   │   ├── models.py            # Modelos SQLAlchemy (ORM)
│   │   ├── session.py           # Engines/Sessions (RW y RO si aplica)
│   │   └── migrations/           # Alembic
│   ├── auth/                    # JWT, hashing, permisos
│   └── repositories/             # Acceso a datos por feature
├── contracts/                   # Schemas Pydantic: Request/Response públicos + códigos de error
└── core/                        # Settings (pydantic-settings), logging, seguridad

tests/
├── unit/
├── integration/                  # Contra Postgres real (testcontainers)
└── architecture/                  # Verifica que las capas no se violen (import-linter)
```

**Regla de dependencias** (igual que en TamboBI): `api → application → domain`,
`infrastructure → application/domain` (nunca al revés). `domain` no importa nada
de las otras capas. Esto se puede forzar automáticamente con `import-linter`
(ver sección de testing).

## 2. Idioma de nombres — convención bilingüe

Igual que en el backend de TamboBI, separamos dos audiencias:

- **Contrato público de la API** (rutas, nombres de campos JSON, valores de
  enums, códigos de error, códigos de permisos) → **inglés**, porque lo
  consume el frontend y potencialmente terceros.
- **Código interno** (nombres de funciones, variables, clases de servicios,
  entidades de dominio, comentarios) → **español**, porque el equipo piensa
  y discute el dominio en español; mejora la legibilidad y el onboarding.

Ejemplo:

```python
# domain/constants/permisos.py
class Permisos:
    """Códigos de permiso: valores en inglés (contrato API).
    Nombres Python en español para legibilidad."""

    ANIMALES_LEER = "animals.read"
    RELOTEOS_LEER = "relotings.read"


# application/interfaces/servicio_animales.py
class IServicioAnimales(Protocol):
    async def obtener_ficha_medica(
        self, herd_id: str, id_vaca: str
    ) -> AnimalMedicalRecordResponse: ...
```

Como Python usa `snake_case` (PEP 8) y no `camelCase`, pero el frontend
espera JSON en camelCase, los schemas de `contracts/` deben generar el JSON
en camelCase automáticamente:

```python
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class AnimalMedicalRecordResponse(ApiModel):
    cow_id: str  # -> "cowId" en el JSON
    group_change_id: int  # -> "groupChangeId" en el JSON
```

Rutas siempre en inglés: `/api/v1/herds/{herd_id}/animals/{cow_id}/medical-record`.

## 3. Patrones a replicar (traducidos a FastAPI)

| Patrón en TamboBI (.NET)                          | Equivalente en FastAPI                                                            |
|-----------------------------------------------------|-------------------------------------------------------------------------------------|
| `[RequierePermiso("x.read")]`                       | `Depends(requiere_permiso("x.read"))` — dependencia que valida claim JWT `permission` |
| `[RequiereAccesoEstablecimiento]`                   | `Depends(requiere_acceso_establecimiento())` — valida claim `herd` o consulta DB con cache |
| `ExceptionHandlingMiddleware` → `ProblemDetails`     | `@app.exception_handler(Exception)` devolviendo `application/problem+json` con `code` y `traceId` |
| DB RW (`ApplicationDbContext`) + RO (`AnalyticsReadDbContext`) | Dos engines SQLAlchemy (uno RW con Alembic, uno RO sin migraciones, `execution_options(readonly=True)`) |
| `SqlQueryRaw` + clases `*Sql.cs` para queries de analytics | `sqlalchemy.text()` en `infrastructure/repositories/*_sql.py` para queries de lectura pesadas |
| `IMemoryCache` con TTL corto                         | `cachetools.TTLCache` (in-memory) o Redis si hay más de una instancia               |
| Rate limiting por policy                             | `slowapi` (basado en `limits`) o `fastapi-limiter` (Redis)                          |
| Response compression (Brotli/Gzip)                   | `GZipMiddleware` (Starlette) + `brotli-asgi`                                        |
| Health checks a ambas DB                             | Endpoint `/health` propio verificando ambas conexiones                              |
| CORS con credenciales                                | `CORSMiddleware`                                                                     |
| Prefijo `/api/v1`                                    | `APIRouter(prefix="/api/v1")`                                                       |
| JWT + refresh tokens                                 | `PyJWT` o `python-jose`, cookies/headers Bearer, refresh token rotativo en DB       |
| Migraciones solo de la DB de escritura                | Alembic apuntando solo a la DB `app`; la DB de analytics la puebla un proceso externo |

## 4. Stack recomendado

**Base**
- **FastAPI** + **Uvicorn** (o **Granian** si se busca más performance)
- **Pydantic v2** para contratos (`contracts/`)
- **SQLAlchemy 2.0 (async, `asyncpg`)** como ORM para la DB de escritura
- **Alembic** para migraciones
- **PostgreSQL 16**
- **uv** como gestor de paquetes/entornos (reemplaza pip/poetry, mucho más rápido)

**Auth y seguridad**
- **PyJWT** o **python-jose** para tokens
- **argon2-cffi** (o `passlib[argon2]`) para hashing de contraseñas (preferido sobre bcrypt)
- **pydantic-settings** para configuración/secrets vía env vars (nunca commitear `.env`)

**Calidad de código**
- **ruff** (lint + format, reemplaza flake8/black/isort)
- **mypy** o **pyright** en modo estricto
- **pre-commit** con esos hooks
- **import-linter** para forzar las reglas de capas (equivalente a `TamboBI.ArchitectureTests`)

**Testing**
- **pytest** + **pytest-asyncio**
- **httpx.AsyncClient** (o `TestClient` de FastAPI) para tests de integración
- **testcontainers-python** para levantar Postgres real en integration tests
- **polyfactory** o **factory_boy** para fixtures/factories

**Observabilidad**
- **structlog** (o `logging` + `python-json-logger`) para logs estructurados
- **asgi-correlation-id** para el `traceId` en cada request/log
- **OpenTelemetry** si el proyecto lo justifica (tracing distribuido)

**Infraestructura**
- **Docker + docker-compose** (Postgres local, igual que `Back/docker-compose.yml`)
- **GitHub Actions** para CI (ruff, mypy, pytest, `alembic check`)
- Si hace falta un pipeline/ETL como el "motor" que puebla Gold en TamboBI:
  **Arq** (async, liviano, sobre Redis) antes que Celery si el equipo es chico

**Opcional según el dominio del proyecto**
- **Redis** si se necesita cache compartido entre instancias o rate limiting distribuido
- **SQLModel** como alternativa más liviana a SQLAlchemy+Pydantic si el proyecto es simple
  (pero para algo con la complejidad de TamboBI, SQLAlchemy 2.0 async da más control)

## 5. Qué simplificar respecto al backend de .NET

Al ser dos personas, no repliquen la separación en 5 proyectos/DLLs con
referencias — en Python alcanza con paquetes dentro de un mismo repo, y
`import-linter` cuida los límites de capas sin la ceremonia de compilación
de .NET. Documenten en `docs/*.md` por feature igual que TamboBI (ayuda
mucho a mantener el conocimiento compartido con dos devs).

## 6. Decisiones pendientes de charlar con el equipo

- ¿Van a necesitar una segunda base de datos de solo lectura (como el Gold
  de TamboBI) o alcanza con una sola?
- ¿Mantienen la convención bilingüe (código en español / contrato en inglés)
  o prefieren todo en inglés por si el proyecto se abre a más gente?
