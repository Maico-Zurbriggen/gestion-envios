# Adenda Técnica — Ajustes al Documento Backend (HU01 y HU02)

**Proyecto:** Sistema de Gestión de Envíos y Distribución
**Materia:** Ingeniería y Calidad de Software
**Destinatario:** Antigravity IDE (Agente de Desarrollo Backend)
**Relación con el documento base:** Este archivo complementa a `backend_prompt_HU01_HU02.md`. Debe leerse junto a ese documento antes de comenzar la implementación; donde haya conflicto, esta adenda tiene prioridad por ser la versión corregida.

---

## A. Datos Semilla (Seed Data)

El Escenario 1 de HU01 asume que el Superadministrador ya cuenta con **credenciales precargadas**. Esto debe resolverse mediante un script de siembra (seed/migration) ejecutado antes de levantar el sistema por primera vez.

### A.1. Tabla `roles`
Insertar los siguientes registros base:

```sql
INSERT INTO roles (id, nombre, descripcion) VALUES
(1, 'SUPERADMIN', 'Administrador general del sistema'),
(2, 'ADMINISTRATIVO', 'Usuario administrativo operativo'),
(3, 'VENDEDOR', 'Personal de terminal / venta'),
(4, 'REPARTIDOR', 'Personal de reparto');
```

### A.2. Usuario Superadministrador inicial
Insertar un único usuario con rol `SUPERADMIN`. A diferencia de los empleados dados de alta por HU01, **este usuario NO debe requerir cambio de contraseña en su primer acceso** (no aplica el flujo de HU02 al Superadmin, según el Escenario 1 de HU01, que da acceso directo con credenciales precargadas):

```sql
-- password_hash generado con BCrypt/Argon2 a partir de la contraseña definida en variable de entorno (ver sección D)
INSERT INTO usuarios (nombre, dni, email, telefono, password_hash, estado, requiere_cambio_password, rol_id)
VALUES ('Admin General', '00000000', 'admin@empresa.com', '+5493564000000', '<hash generado en script>', 'Activo', FALSE, 1);
```

**Instrucción para Antigravity IDE:** el script de seed debe leer la contraseña del Superadmin desde una variable de entorno (nunca hardcodeada en texto plano en el repositorio) y generar su hash en tiempo de ejecución del seed.

---

## B. Unificación de la Política de Contraseña Temporal

El documento base presenta dos definiciones distintas de la contraseña temporal generada automáticamente:
- Sección 3 (HU01, Escenario 3): "contraseña temporal alfanumérica".
- Sección 5.2: "8-12 caracteres alfanuméricos con mayúsculas, minúsculas y símbolos".

**Regla única a aplicar (reemplaza ambas):**

> La contraseña temporal generada automáticamente debe tener entre 10 y 12 caracteres, e incluir al menos: una letra mayúscula, una letra minúscula, un número y un símbolo especial (`! @ # $ % & *`). Debe generarse con un PRNG criptográficamente seguro (ej. `crypto.randomBytes` o equivalente del lenguaje elegido).

Esta misma regla de complejidad es la que debe validarse también en el endpoint de cambio de contraseña (`/api/v1/auth/cambiar-password`), de modo que la política sea consistente en todo el sistema y no haya dos estándares distintos de "contraseña válida".

---

## C. Esquema Estándar de Respuestas de Error

El documento base indica que las respuestas deben ser "estructuradas uniformemente en formato JSON" pero no define un esquema concreto para los errores `400` y `409`. Usar el siguiente formato en **todos** los endpoints de HU01 y HU02:

```json
{
  "status": "error",
  "code": "VALIDATION_ERROR",
  "message": "Los datos proporcionados no son válidos.",
  "errors": [
    { "field": "dni", "message": "El DNI debe contener solo dígitos." },
    { "field": "email", "message": "El formato de email no es válido." }
  ]
}
```

Códigos (`code`) sugeridos por caso:
| Situación | HTTP | `code` |
|---|---|---|
| Credenciales inválidas en login | 401 | `AUTH_FAILED` |
| Payload con formato inválido | 400 | `VALIDATION_ERROR` |
| DNI o email ya registrado | 409 | `DUPLICATE_ENTRY` |
| Nueva contraseña no cumple política o no coincide con confirmación | 400 | `PASSWORD_POLICY_ERROR` |
| Token JWT ausente, inválido o con scope insuficiente | 401 / 403 | `INVALID_TOKEN` / `FORBIDDEN_SCOPE` |

El array `errors` puede tener uno o varios elementos según cuántos campos fallen; si el error no es de validación de campos (ej. `AUTH_FAILED`), puede omitirse el array y dejar solo `message`.

---

## D. Variables de Entorno / Configuración

El documento base no especifica dónde deben vivir los valores de configuración sensibles. Antigravity IDE debe crear un archivo de ejemplo (`.env.example`) con, como mínimo:

```
DATABASE_URL=
JWT_SECRET=
JWT_EXPIRATION=8h
JWT_TEMP_TOKEN_EXPIRATION=15m
BCRYPT_SALT_ROUNDS=12
SUPERADMIN_SEED_PASSWORD=
SUPERADMIN_SEED_DNI=
SUPERADMIN_SEED_EMAIL=
```

Notas:
- `BCRYPT_SALT_ROUNDS` fija en 12 el "salting factor ≥10" que menciona el documento base, para que no varíe entre entornos de desarrollo del equipo.
- `JWT_TEMP_TOKEN_EXPIRATION` corresponde al token de scope restringido (`PASSWORD_RESET_ONLY`) emitido en el primer acceso (HU02, Escenario 1); debe ser corto para reducir la ventana de uso indebido.
- Ningún valor de esta lista debe commitearse con datos reales; solo el archivo `.env.example` vacío va al repositorio.

---

## E. Trazabilidad de Criterios de Aceptación (CA)

La Pila de Sprint 1 (hojas HU01 y HU02 del Excel) referencia criterios `CA1` a `CA6`, pero el Product Backlog original solo define 4 escenarios BDD por historia. Para evitar ambigüedad al momento de mapear tareas a criterios:

- Usar como **única fuente de verdad** los 4 Escenarios BDD definidos en la Sección 3 del documento base (`backend_prompt_HU01_HU02.md`), no la numeración CA1–CA6 de la pila.
- Si en el futuro se necesita trazabilidad fila por fila entre la pila y los escenarios, se recomienda renumerar las tareas de la pila para que cada `CA` corresponda a un Escenario existente, en lugar de agregar criterios nuevos no documentados.

---

## F. Resumen de Cambios Respecto al Documento Base

| Punto | Sección afectada del documento base | Acción |
|---|---|---|
| Seed de Superadmin y roles | Sección 4 (Esquema SQL) | Agregar script de siembra (Sección A de esta adenda) |
| Política de contraseña temporal | Secciones 3 y 5.2 | Unificar bajo una sola regla (Sección B) |
| Formato de errores 400/409 | Sección 5 (Endpoints) | Adoptar esquema estándar (Sección C) |
| Configuración sensible | Sección 6 (Reglas de negocio) | Definir variables de entorno (Sección D) |
| Numeración de criterios de aceptación | Pila de Sprint (Excel) vs. Sección 3 | Usar Escenarios 1–4 como fuente única (Sección E) |
