# Estrategia de pruebas

## Cómo correrlas

```powershell
& .\.venv\Scripts\python.exe -m pytest -q
```

Para correr solo una carpeta: `pytest tests/unit`, `pytest tests/integration`, `pytest tests/architecture`.

## Las tres carpetas

### `tests/unit/`

Prueban funciones puras de dominio y utilidades de infraestructura, sin tocar la base de datos ni levantar la app: `test_password_rules.py`, `test_paquete_rules.py`, `test_codigos_rules.py`, `test_hasher.py`, `test_jwt.py`. Son las más rápidas y las primeras que conviene correr al modificar una regla de negocio en `domain/rules/`.

### `tests/integration/`

Levantan la aplicación FastAPI completa (`app.api.main:app`) contra una base SQLite **en memoria**, y hacen requests HTTP reales con `httpx.AsyncClient` (sin sockets, vía `ASGITransport` — no hace falta un servidor corriendo). Es donde viven los tests trazables a los escenarios BDD del Product Backlog: `test_auth_flow.py` (HU01/HU02), `test_admin_empleados.py` (HU01), `test_security_scopes.py` (autorización transversal), `test_envios_registro.py` (HU03), `test_seguimiento.py` (HU04), `test_sucursales.py`.

Cómo está armado (`tests/conftest.py`):

- `db_session`: crea todas las tablas en una base en memoria (`sqlite+aiosqlite:///:memory:`) para **cada test individual** (fixture de scope `function`), siembra los 4 roles, el Superadministrador y 2 sucursales de prueba, y al terminar el test borra todas las tablas. Esto garantiza que los tests no comparten estado entre sí ni con la base de desarrollo real (`gestion_envios.db`).
- `client`: un `AsyncClient` que sobreescribe la dependencia `obtener_sesion_db` de FastAPI (`app.dependency_overrides`) para que la app use esa misma sesión en memoria en vez de conectarse a la base real.
- `superadmin_token`: un JWT `FULL_ACCESS` con rol `SUPERADMIN`, listo para usar en el header `Authorization` de un test que necesite un endpoint protegido.

Convención de nombres: los tests que verifican un escenario BDD puntual del Product Backlog se nombran `test_hu0X_escenario_Y_...`, para poder ubicar rápido qué test cubre qué criterio de aceptación.

### `tests/architecture/`

`test_architecture_layers.py` no prueba comportamiento, prueba la **estructura** del código: recorre el árbol de sintaxis (AST) de cada archivo en `app/domain` y `app/application` y falla si encuentra un `import` de una capa que no debería conocer (ver [Capas y estructura](../01-arquitectura/capas-y-estructura.md)). Es la forma de que la regla de dependencias de Clean Architecture no dependa solo de la disciplina del equipo — si alguien por error hace `from fastapi import ...` dentro de `domain/`, el test falla explícitamente con el archivo y el import problemático.

## Qué falta cubrir

- No hay tests de los manejadores de excepciones genéricos de `api/middleware.py` para el caso `500 INTERNAL_ERROR` (el "error no controlado") — los tests actuales solo ejercitan las excepciones de negocio explícitas.
- No hay tests de que `crear_tablas()` / el seed sean realmente idempotentes contra una base persistente (los tests de integración usan una base en memoria que se recrea por test, no el flujo de arranque real).
- A medida que se implementen las próximas historias (HU05 en adelante), agregar su archivo de test siguiendo la misma convención de nombres y, si corresponde, documentar el escenario en `04-historias-de-usuario/`.