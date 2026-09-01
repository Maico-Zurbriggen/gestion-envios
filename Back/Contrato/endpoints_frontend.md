# Documentación de Endpoints de la API Backend (Para Frontend)

**Proyecto:** Sistema de Gestión de Envíos y Distribución  
**Versión API:** v1 (`/api/v1`)  
**Formato de Intercambio:** `JSON` (Content-Type: `application/json`)  
**Base URL Local:** `http://localhost:8000` (con prefijo `/api/v1`)

---

## 📌 Índice de Endpoints

1. [Esquema Estándar de Respuestas](#1-esquema-estándar-de-respuestas)
2. [Tabla de Roles y Números Asociados](#2-tabla-de-roles-y-números-asociados)
3. [Endpoints de Autenticación (`/auth`)](#3-endpoints-de-autenticación)
   - `POST /api/v1/auth/login` (Login con DNI y Contraseña)
   - `POST /api/v1/auth/login-token` (Login / Validación con Token JWT)
   - `GET /api/v1/auth/me` (Consultar Perfil del Usuario Autenticado)
   - `POST /api/v1/auth/cambiar-password` (Cambio Obligatorio de Contraseña)
4. [Endpoints de Roles (`/roles`)](#4-endpoints-de-roles)
   - `GET /api/v1/roles` (Listado de Roles e IDs)
5. [Endpoints de Administración (`/admin`)](#5-endpoints-de-administración)
   - `POST /api/v1/admin/empleados` (Alta de Empleado por Superadmin)
6. [Endpoints de Monitoreo (`/health`)](#6-endpoints-de-monitoreo)
   - `GET /health` o `GET /api/v1/health` (Health Check)

---

## 1. Esquema Estándar de Respuestas

### ✅ Respuesta Exitosa Estándar
```json
{
  "status": "success",
  "message": "Mensaje opcional informativo",
  "data": { ... }
}
```

### ⚠️ Respuesta de Primer Acceso (Cambio de Clave Requerido)
```json
{
  "status": "requires_password_change",
  "message": "Debe cambiar su contraseña temporal antes de continuar.",
  "data": {
    "temp_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "requiere_cambio_password": true
  }
}
```

### ❌ Respuesta de Error Estándar (`400`, `401`, `403`, `409`, `500`)
```json
{
  "status": "error",
  "code": "CODIGO_ERROR",
  "message": "Descripción amigable del error.",
  "errors": [
    {
      "field": "nombre_campo",
      "message": "Detalle del error en este campo."
    }
  ]
}
```

#### Códigos de Error Principales (`code`):
* `AUTH_FAILED`: Credenciales inválidas o usuario inactivo (HTTP 401).
* `INVALID_TOKEN`: Token no provisto, inválido o expirado (HTTP 401).
* `FORBIDDEN_SCOPE`: El token posee un scope restringido (por ejemplo, `PASSWORD_RESET_ONLY`) y no puede consumir la ruta (HTTP 403).
* `FORBIDDEN_ACCESS`: El usuario no posee el rol o permisos necesarios (HTTP 403).
* `VALIDATION_ERROR`: Fallo de validación de formato en campos (HTTP 400).
* `PASSWORD_POLICY_ERROR`: Contraseña no cumple las reglas de seguridad o no coincide la confirmación (HTTP 400).
* `DUPLICATE_ENTRY`: DNI o Email ya registrados (HTTP 409).

---

## 2. Tabla de Roles y Números Asociados

El frontend debe utilizar los siguientes IDs numéricos para la asignación y filtrado de roles:

| `id` (int) | `nombre` (string) | Descripción | Permisos Principales |
|:---:|:---|:---|:---|
| **1** | `SUPERADMIN` | Administrador general del sistema | Alta de empleados, acceso total |
| **2** | `ADMINISTRATIVO` | Usuario administrativo operativo | Gestión y seguimiento de envíos |
| **3** | `VENDEDOR` | Personal de terminal / venta | Registro de órdenes y ventas |
| **4** | `REPARTIDOR` | Personal de reparto | Gestión de rutas y entregas |

---

## 3. Endpoints de Autenticación

### 3.1. Login con DNI y Contraseña
Permite a cualquier usuario (Superadmin o empleados) iniciar sesión con DNI y contraseña.

* **Método:** `POST`
* **URL:** `/api/v1/auth/login`
* **Autenticación requerida:** No (Público)
* **Headers:** `Content-Type: application/json`
* **Request Body:**
```json
{
  "dni": "12345678",
  "password": "PasswordTemporal123!"
}
```

* **Respuestas:**
  * **`200 OK` (Login Normal - Acceso Pleno Otorgado):**
    ```json
    {
      "status": "success",
      "data": {
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "user": {
          "id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
          "nombre": "Admin General",
          "dni": "12345678",
          "email": "admin@empresa.com",
          "rol": "SUPERADMIN",
          "requiere_cambio_password": false
        }
      }
    }
    ```
    > 💡 **Nota Front:** Guardar `token` en `localStorage` o cookies y redirigir al Dashboard.

  * **`200 OK` (Primer Acceso Requerido - Redirigir a Cambio de Contraseña):**
    ```json
    {
      "status": "requires_password_change",
      "message": "Debe cambiar su contraseña temporal antes de continuar.",
      "data": {
        "temp_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "requiere_cambio_password": true
      }
    }
    ```
    > 💡 **Nota Front:** Redirigir a la pantalla de cambio de clave obligatoria utilizando `temp_token`.

  * **`401 Unauthorized`:**
    ```json
    {
      "status": "error",
      "code": "AUTH_FAILED",
      "message": "Credenciales inválidas."
    }
    ```

---

### 3.2. Login / Validación mediante Token JWT
Permite validar un token previamente obtenido y autenticar la sesión del usuario directamente sin solicitar nuevamente DNI y clave.

* **Método:** `POST`
* **URL:** `/api/v1/auth/login-token`
* **Autenticación requerida:** Token JWT (por Body o por Header)
* **Headers:** `Content-Type: application/json` y/o `Authorization: Bearer <token>`
* **Request Body (Opcional si se envía en Header):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

* **Respuestas:**
  * **`200 OK` (Sesión Válida - Acceso Pleno):**
    ```json
    {
      "status": "success",
      "data": {
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "user": {
          "id": "c1f82b71-12a3-4aef-bc82-9a1122334455",
          "nombre": "Carlos Gómez",
          "dni": "35123456",
          "email": "carlos.gomez@empresa.com",
          "rol": "ADMINISTRATIVO",
          "requiere_cambio_password": false
        }
      }
    }
    ```
  * **`401 Unauthorized` (Token expirado o inválido):**
    ```json
    {
      "status": "error",
      "code": "INVALID_TOKEN",
      "message": "El token ha expirado."
    }
    ```

---

### 3.3. Consultar Perfil del Usuario Autenticado (`/me`)
Permite al frontend obtener la información del usuario en sesión a partir del token guardado.

* **Método:** `GET`
* **URL:** `/api/v1/auth/me`
* **Autenticación requerida:** Sí (`Authorization: Bearer <token>`)
* **Headers:** `Authorization: Bearer <token>`
* **Respuestas:**
  * **`200 OK`:**
    ```json
    {
      "status": "success",
      "data": {
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "user": {
          "id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
          "nombre": "Admin General",
          "dni": "12345678",
          "email": "admin@empresa.com",
          "rol": "SUPERADMIN",
          "requiere_cambio_password": false
        }
      }
    }
    ```

---

### 3.4. Cambio Obligatorio de Contraseña
Utilizado en el primer acceso (con `temp_token`) o para cambio voluntario de contraseña (con `auth_token`).

* **Método:** `POST`
* **URL:** `/api/v1/auth/cambiar-password`
* **Autenticación requerida:** Sí (`Authorization: Bearer <temp_token>` o `<auth_token>`)
* **Headers:**
  - `Content-Type: application/json`
  - `Authorization: Bearer <temp_token>`
* **Política de Seguridad de Contraseña:**
  - Entre 10 y 12 caracteres (o más).
  - Al menos 1 mayúscula.
  - Al menos 1 minúscula.
  - Al menos 1 número.
  - Al menos 1 carácter especial (`! @ # $ % & *`).
* **Request Body:**
```json
{
  "password_actual": "Tmp#9284Kz1!",
  "nueva_password": "MiNuevaPasswordSegura2026!",
  "confirmacion_password": "MiNuevaPasswordSegura2026!"
}
```

* **Respuestas:**
  * **`200 OK` (Cambio Exitoso):**
    ```json
    {
      "status": "success",
      "message": "Contraseña actualizada exitosamente. Ya puede operar normalmente.",
      "data": {
        "auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
      }
    }
    ```
    > 💡 **Nota Front:** Guardar el nuevo `auth_token` recibido y redirigir al Dashboard principal.

  * **`400 Bad Request` (Error en Política o No coinciden):**
    ```json
    {
      "status": "error",
      "code": "PASSWORD_POLICY_ERROR",
      "message": "Las contraseñas no coinciden o no cumplen con los requisitos de seguridad.",
      "errors": [
        {
          "field": "nueva_password",
          "message": "La contraseña debe tener al menos 10 caracteres e incluir mayúscula, minúscula, número y símbolo (!@#$%&*)."
        }
      ]
    }
    ```

---

## 4. Endpoints de Roles

### 4.1. Listado Completo de Roles e IDs
Permite al Frontend obtener la lista de roles para poblar selectores, desplegables y asociar IDs en altas o filtros.

* **Método:** `GET`
* **URL:** `/api/v1/roles`
* **Autenticación requerida:** No (Público)
* **Headers:** `Content-Type: application/json`
* **Respuestas:**
  * **`200 OK`:**
    ```json
    {
      "status": "success",
      "data": [
        {
          "id": 1,
          "nombre": "SUPERADMIN",
          "descripcion": "Administrador general del sistema"
        },
        {
          "id": 2,
          "nombre": "ADMINISTRATIVO",
          "descripcion": "Usuario administrativo operativo"
        },
        {
          "id": 3,
          "nombre": "VENDEDOR",
          "descripcion": "Personal de terminal / venta"
        },
        {
          "id": 4,
          "nombre": "REPARTIDOR",
          "descripcion": "Personal de reparto"
        }
      ]
    }
    ```

---

## 5. Endpoints de Administración

### 5.1. Alta de Empleado (por Superadministrador)
Permite al Superadministrador dar de alta nuevos empleados administrativos o de otras áreas.

* **Método:** `POST`
* **URL:** `/api/v1/admin/empleados`
* **Autenticación requerida:** Sí (`Authorization: Bearer <token_superadmin>` con rol `SUPERADMIN`)
* **Headers:**
  - `Content-Type: application/json`
  - `Authorization: Bearer <token>`
* **Request Body:**
```json
{
  "nombre": "Carlos Gómez",
  "dni": "35123456",
  "email": "carlos.gomez@empresa.com",
  "telefono": "+543564123456",
  "rol_id": 2
}
```

* **Respuestas:**
  * **`201 Created`:**
    ```json
    {
      "status": "success",
      "message": "Empleado creado correctamente.",
      "data": {
        "id": "c1f82b71-12a3-4aef-bc82-9a1122334455",
        "nombre": "Carlos Gómez",
        "dni": "35123456",
        "email": "carlos.gomez@empresa.com",
        "telefono": "+543564123456",
        "estado": "Activo",
        "rol": "ADMINISTRATIVO",
        "password_temporal": "Tmp#9284Kz1!"
      }
    }
    ```
    > 💡 **Nota Front:** Mostrar en modal/alerta la `password_temporal` para que el Superadmin pueda entregarla al empleado.

  * **`400 Bad Request`:**
    ```json
    {
      "status": "error",
      "code": "VALIDATION_ERROR",
      "message": "Los datos proporcionados no son válidos.",
      "errors": [
        {
          "field": "dni",
          "message": "El DNI debe contener solo dígitos."
        }
      ]
    }
    ```

  * **`403 Forbidden`:**
    ```json
    {
      "status": "error",
      "code": "FORBIDDEN_ACCESS",
      "message": "Acceso denegado. Se requiere rol SUPERADMIN."
    }
    ```

  * **`409 Conflict` (DNI o Email ya registrados):**
    ```json
    {
      "status": "error",
      "code": "DUPLICATE_ENTRY",
      "message": "El DNI o correo electrónico ya se encuentra registrado."
    }
    ```

---

## 6. Endpoints de Monitoreo

### 6.1. Health Check
* **Método:** `GET`
* **URL:** `/health` o `/api/v1/health`
* **Autenticación:** No
* **Respuesta (`200 OK`):**
```json
{
  "status": "healthy",
  "service": "Sistema de Gestión de Envíos Backend"
}
```

---

## 🔄 Resumen del Flujo de Autenticación para el Frontend

```
                       [ Pantalla de Login ]
                                 │
                   POST /api/v1/auth/login (DNI + Password)
                                 │
                 ┌───────────────┴───────────────┐
        status == "success"            status == "requires_password_change"
                 │                               │
       Guardar 'token'                 Guardar 'temp_token'
                 │                               │
         [ Ir a Dashboard ]            [ Redirigir a Cambiar Clave ]
                                                 │
                                 POST /api/v1/auth/cambiar-password
                                 (Header: Bearer temp_token)
                                                 │
                                       status == "success"
                                                 │
                                       Guardar 'auth_token'
                                                 │
                                         [ Ir a Dashboard ]
```

