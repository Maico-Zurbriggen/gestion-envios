# Capas y estructura del proyecto

El backend sigue una Clean Architecture adaptada a Python: en vez de separar en varios proyectos/DLL como en un backend .NET, las capas son *paquetes* dentro de un único proyecto. La guía original de esta decisión está en [`Back/Contexto/arquitectura-backend-fastapi.md`](../../Contexto/arquitectura-backend-fastapi.md); este documento describe cómo quedó aplicada en la práctica.

## Estructura real

```text
app/
├── api/                       # Capa de presentación (HTTP)
│   ├── v1/routers/            # Un router por recurso: auth, admin, envios, seguimiento, sucursales, health
│   ├── dependencies.py        # Depends() reutilizables: inyección de servicios/repos, auth, roles, scopes
│   ├── middleware.py          # Manejadores de excepciones globales → respuestas JSON uniformes
│   └── main.py                # Fábrica de la app FastAPI, wiring de routers y middlewares
├── application/                # Casos de uso
│   ├── interfaces/             # Protocols (equivalentes a interfaces IServicioX / IRepositorioX)
│   └── services/                # Implementación de los casos de uso (ServicioAuth, ServicioEnvios, etc.)
├── domain/                     # Reglas de negocio puras, sin I/O
│   ├── constants/               # Roles, scopes de JWT, códigos de error
│   ├── entities/                 # Dataclasses de dominio (Usuario, Rol) — ver nota de dead code más abajo
│   └── rules/                    # Validaciones de paquete, contraseñas, generación de códigos
├── infrastructure/              # Implementaciones concretas
│   ├── auth/                     # Hasher (BCrypt) y manejador de JWT
│   ├── db/                        # Modelos SQLAlchemy, sesión async, seed, migraciones (Alembic)
│   └── repositories/               # Implementación de los Protocols de application/interfaces con SQLAlchemy
├── contracts/                    # Schemas Pydantic de request/response por feature (auth, empleados, envios, seguimiento, sucursales)
└── core/                          # Settings, logging, excepciones de aplicación

tests/
├── unit/            # Reglas de dominio puras (sin DB): password_rules, paquete_rules, codigos_rules, hasher, jwt
├── integration/     # Contra la app FastAPI completa + SQLite en memoria (httpx.AsyncClient)
└── architecture/    # Verifica con AST que domain/application no importen capas prohibidas
```

## Regla de dependencias

`api → application → domain`, `infrastructure → application/domain` (nunca al revés). `domain` no debe importar nada de `api`, `application`, `infrastructure`, `fastapi` ni `sqlalchemy`. Esto no se fuerza con una herramienta como `import-linter` (a diferencia de lo que sugería la guía original) sino con tests propios en `tests/architecture/test_architecture_layers.py`, que recorren el árbol de sintaxis (AST) de cada archivo y fallan si detectan un import prohibido. Correr `pytest tests/architecture` es la forma rápida de confirmar que la regla se sigue respetando.

## Flujo típico de una request

Usando `POST /api/v1/envios` como ejemplo (HU03):

1. `api/v1/routers/envios.py` recibe la request, ya validada contra `contracts/envios.py:CrearEnvioRequest` (Pydantic).
2. FastAPI resuelve las dependencias declaradas con `Depends(...)` en `api/dependencies.py`, que arman `ServicioEnvios` inyectándole sus repositorios (`RepositorioEnvios`, `RepositorioSucursales`) ya conectados a la sesión de base de datos de la request.
3. `application/services/servicio_envios.py` ejecuta el caso de uso: valida reglas de dominio (`domain/rules/paquete_rules.py`), genera identificadores únicos (`domain/rules/codigos_rules.py`) y arma las entidades SQLAlchemy.
4. `infrastructure/repositories/repositorio_envios.py` persiste esas entidades y las vuelve a leer con sus relaciones (`sucursal_destino`, `paquetes`) cargadas.
5. El servicio devuelve un `CrearEnvioResponse` (contrato Pydantic), que FastAPI serializa a JSON.
6. Si algo falla en cualquier capa, se lanza una subclase de `AppException` (`core/exceptions.py`) y los manejadores globales de `api/middleware.py` la convierten en una respuesta JSON con el formato estándar (ver [Manejo de errores](../03-seguridad/manejo-de-errores.md)).

## Convención de idioma

- Contrato público de la API (rutas, campos JSON, valores de enums, códigos de error) → **español**, salvo los nombres de rutas que ya quedaron en español desde el inicio del proyecto (`/envios`, `/seguimiento`, `/sucursales`, `/admin/empleados`). A diferencia de la guía inicial (que sugería inglés para el contrato público, por analogía con TamboBI), el equipo decidió mantener todo en español de punta a punta, dado que el proyecto es 100% interno y en español.
- Código interno (nombres de clases, funciones, variables, docstrings) → español.

## Nota: entidades de dominio sin usar

`domain/entities/usuario.py` y `domain/entities/rol.py` definen dataclasses (`Usuario`, `Rol`) que no se usan en ningún flujo actual — los servicios trabajan directamente con los modelos SQLAlchemy de `infrastructure/db/models.py` (`UsuarioModel`, `RolModel`). Quedaron del scaffolding inicial de la arquitectura. No se eliminaron en esta etapa porque no generan ningún problema funcional, pero si el equipo decide en el futuro introducir una capa de dominio real desacoplada del ORM, es el punto de partida natural.