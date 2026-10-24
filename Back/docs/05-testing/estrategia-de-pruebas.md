# Estrategia de pruebas

## Cómo correrlas

```powershell
& .\.venv\Scripts\python.exe -m pytest -q
```

Para correr solo una carpeta: `pytest tests/unit`, `pytest tests/integration`, `pytest tests/architecture`.

## Las tres carpetas

### `tests/unit/`

Prueban funciones puras de dominio y utilidades de infraestructura, sin tocar la base de datos ni levantar la app: `test_password_rules.py`, `test_paquete_rules.py`, `test_codigos_rules.py`, `test_retiro_rules.py` (HU09/HU13), `test_recepcion_rules.py` (HU06), `test_destino_rules.py` (formato compartido HU04/HU06), `test_reclamo_rules.py` (HU07), `test_preguntas_frecuentes_rules.py` (HU08), `test_recorrido_rules.py` (HU10: el algoritmo de generación completo, incluida una verificación de optimalidad contra fuerza bruta), `test_hasher.py`, `test_jwt.py`. Son las más rápidas y las primeras que conviene correr al modificar una regla de negocio en `domain/rules/`.

### `tests/integration/`

Levantan la aplicación FastAPI completa (`app.api.main:app`) contra una base SQLite **en memoria**, y hacen requests HTTP reales con `httpx.AsyncClient` (sin sockets, vía `ASGITransport` — no hace falta un servidor corriendo). Es donde viven los tests trazables a los escenarios BDD del Product Backlog: `test_auth_flow.py` (HU01/HU02), `test_admin_empleados.py` (HU01), `test_security_scopes.py` (autorización transversal), `test_envios_registro.py` (HU03), `test_seguimiento.py` (HU04), `test_sucursales.py`, `test_hu05_notificaciones.py` (HU05), `test_hu06_recepcion_terminal.py` (HU06), `test_hu07_reclamos.py` (HU07), `test_hu08_preguntas_frecuentes.py` (HU08), `test_hu09_sucursales_retiro.py` (HU09), `test_hu10_recorridos.py` y `test_hu10_repartidores.py` (HU10), `test_hu13_retiro_sucursal.py` (HU13).

`test_flujo_punta_a_punta.py` es distinto: no precarga nada en la base y recorre, solo por HTTP, registro (HU03) → recepción en terminal (HU06) → perfil de repartidor, generación, edición e inicio de recorrido (HU10) → seguimiento público (HU04) → reclamo y su resolución (HU07) → preguntas frecuentes (HU08). Falla si dos historias dejan de encajar entre sí aunque cada una pase sus propios tests.

Cómo está armado (`tests/conftest.py`):

- `db_session`: crea todas las tablas en una base en memoria (`sqlite+aiosqlite:///:memory:`) para **cada test individual** (fixture de scope `function`), siembra los 4 roles, el Superadministrador y 2 sucursales de prueba, y al terminar el test borra todas las tablas. Esto garantiza que los tests no comparten estado entre sí ni con la base de desarrollo real (`gestion_envios.db`).
- `client`: un `AsyncClient` que sobreescribe la dependencia `obtener_sesion_db` de FastAPI (`app.dependency_overrides`) para que la app use esa misma sesión en memoria en vez de conectarse a la base real.
- `superadmin_token`: un JWT `FULL_ACCESS` con rol `SUPERADMIN`, listo para usar en el header `Authorization` de un test que necesite un endpoint protegido.
- `administrativo_usuario` / `administrativo_token`, `vendedor_usuario` / `vendedor_token`, `repartidor_usuario` / `repartidor_token`: usuarios reales persistidos en la base de prueba con su JWT `FULL_ACCESS`. Se necesitan **persistidos** (y no solo un token firmado) porque `requerir_roles` resuelve el usuario en la base: un token con un `sub` inexistente devuelve `401`, no `403`, así que probar el rechazo por rol exige que el usuario exista.

Convención de nombres: los tests que verifican un escenario BDD puntual del Product Backlog se nombran `test_hu0X_escenario_Y_...`, para poder ubicar rápido qué test cubre qué criterio de aceptación.

### `tests/architecture/`

`test_architecture_layers.py` no prueba comportamiento, prueba la **estructura** del código: recorre el árbol de sintaxis (AST) de cada archivo en `app/domain` y `app/application` y falla si encuentra un `import` de una capa que no debería conocer (ver [Capas y estructura](../01-arquitectura/capas-y-estructura.md)). Es la forma de que la regla de dependencias de Clean Architecture no dependa solo de la disciplina del equipo — si alguien por error hace `from fastapi import ...` dentro de `domain/`, el test falla explícitamente con el archivo y el import problemático.

## Qué falta cubrir

- No hay tests de los manejadores de excepciones genéricos de `api/middleware.py` para el caso `500 INTERNAL_ERROR` (el "error no controlado") — los tests actuales solo ejercitan las excepciones de negocio explícitas.
- No hay tests de que `crear_tablas()` / el seed sean realmente idempotentes contra una base persistente (los tests de integración usan una base en memoria que se recrea por test, no el flujo de arranque real).
- A medida que se implementen las próximas historias (HU11, HU12), agregar su archivo de test siguiendo la misma convención de nombres, sumarlas al flujo de punta a punta y documentar el escenario en `04-historias-de-usuario/`.
- Las migraciones no se prueban en `pytest` (los tests usan `create_all`). Al agregar una, verificar a mano `alembic upgrade head`, `alembic downgrade -1` y `alembic check` contra una base temporal (`DATABASE_URL` apuntando a un archivo descartable).