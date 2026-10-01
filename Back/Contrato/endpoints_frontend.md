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
7. [Endpoints de Retiro de Paquetes en Sucursal (`/sucursal/paquetes`) - HU13](#7-endpoints-de-retiro-de-paquetes-en-sucursal-hu13)
   - `GET /api/v1/sucursal/paquetes/{id_o_codigo}/validar-retiro` (Validar Disponibilidad y Requisitos de Retiro)
   - `POST /api/v1/sucursal/paquetes/{id}/registrar-retiro` (Registrar Retiro por Titular o Tercero Autorizado)
8. [Servicio de Notificación de Token por Correo - HU05](#8-servicio-de-notificación-de-token-por-correo-hu05)
   - Despacho Asíncrono en `POST /api/v1/envios` y Log de Auditoría

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

---

## 7. Endpoints de Retiro de Paquetes en Sucursal (HU13)

Permite al personal de sucursal autenticado con rol `ADMINISTRATIVO` (o `SUPERADMIN`) consultar y asentar la entrega presencial de paquetes en ventanilla, validando la identidad del titular o la acreditación de un tercero autorizado.

### 7.1. Validar Disponibilidad y Requisitos de Retiro
Permite verificar el estado actual del paquete y los datos del destinatario para contrastar identidad física.

* **Método:** `GET`
* **URL:** `/api/v1/sucursal/paquetes/{id_o_codigo}/validar-retiro`
* **Parámetros de Ruta:**
  * `id_o_codigo` (string, obligatorio): Puede ser el UUID del paquete (`d476fa8c-...`) o el código de paquete alfanumérico (`PAQ-XXXXXXXXXX`).
* **Autenticación requerida:** Sí (Header `Authorization: Bearer <JWT_ADMINISTRATIVO>`)
* **Roles Permitidos:** `ADMINISTRATIVO`, `SUPERADMIN`

#### ✅ Respuesta Exitosa (`200 OK`) - Paquete Listo para Retiro:
```json
{
  "status": "success",
  "data": {
    "paquete_id": "d476fa8c-5264-44df-a8b2-6beea61ef1b9",
    "numero_paquete": "PAQ-ZPC5LB48JJ",
    "descripcion": "Ropa y calzado",
    "peso_kg": 2.5,
    "estado_actual": "LISTO_PARA_RETIRO",
    "disponible_para_retiro": true,
    "motivo_no_disponible": null,
    "tipo_entrega": "sucursal",
    "sucursal_destino": {
      "id": 1,
      "nombre": "Sucursal Córdoba Centro",
      "provincia": "Córdoba",
      "ciudad": "Córdoba",
      "direccion": "Av. Colón 1234",
      "latitud": -31.4167,
      "longitud": -64.1833
    },
    "sucursal_actual": {
      "id": 1,
      "nombre": "Sucursal Córdoba Centro",
      "provincia": "Córdoba",
      "ciudad": "Córdoba",
      "direccion": "Av. Colón 1234",
      "latitud": -31.4167,
      "longitud": -64.1833
    },
    "datos_destinatario": {
      "nombre": "María López",
      "telefono": "+543564333444",
      "email": "maria.lopez@example.com"
    },
    "requisitos_retiro": {
      "titular": "Presentar documento de identidad original y acreditar ser mayor de 16 años.",
      "tercero_autorizado": "Presentar documento de identidad propio, copia del documento del titular y constancia/formulario de autorización de retiro firmada por el destinatario."
    }
  }
}
```

#### ⚠️ Respuesta Exitosa (`200 OK`) - Paquete NO Disponible para Retiro:
Si el paquete existe pero su estado es `EN_TRANSITO`, `EN_REPARTO` o ya fue entregado previamente (`ENTREGADO_EN_SUCURSAL`, `RETIRADO`):
```json
{
  "status": "success",
  "data": {
    "paquete_id": "d476fa8c-5264-44df-a8b2-6beea61ef1b9",
    "numero_paquete": "PAQ-ZPC5LB48JJ",
    "descripcion": "Ropa y calzado",
    "peso_kg": 2.5,
    "estado_actual": "EN_TRANSITO",
    "disponible_para_retiro": false,
    "motivo_no_disponible": "El paquete no se encuentra listo para retiro en sucursal. Estado actual: 'EN_TRANSITO'. Debe estar en sucursal para poder retirarse.",
    "tipo_entrega": "sucursal",
    "sucursal_destino": { ... },
    "sucursal_actual": null,
    "datos_destinatario": { ... },
    "requisitos_retiro": { ... }
  }
}
```

#### ❌ Respuestas de Error:
* **`404 Not Found` (Paquete inexistente):**
  ```json
  {
    "status": "error",
    "code": "NOT_FOUND",
    "message": "No se encontró un paquete con el identificador 'PAQ-NOEXISTE'."
  }
  ```
* **`401 Unauthorized` (Token faltante o inválido):**
  ```json
  {
    "status": "error",
    "code": "INVALID_TOKEN",
    "message": "Token de autenticación ausente o inválido."
  }
  ```
* **`403 Forbidden` (Rol insuficiente, ej. Repartidor o Vendedor):**
  ```json
  {
    "status": "error",
    "code": "FORBIDDEN_ACCESS",
    "message": "Acceso denegado. Se requiere uno de los siguientes roles: ADMINISTRATIVO, SUPERADMIN."
  }
  ```

---

### 7.2. Registrar Retiro de Paquete en Sucursal
Registra de forma definitiva y transaccional la entrega del paquete en la ventanilla de la sucursal.

* **Método:** `POST`
* **URL:** `/api/v1/sucursal/paquetes/{id}/registrar-retiro`
* **Parámetros de Ruta:**
  * `id` (string, obligatorio): UUID del paquete o su código alfanumérico (`PAQ-XXXXXXXXXX`).
* **Autenticación requerida:** Sí (Header `Authorization: Bearer <JWT_ADMINISTRATIVO>`)
* **Roles Permitidos:** `ADMINISTRATIVO`, `SUPERADMIN`
* **Headers:** `Content-Type: application/json`

#### 📦 Caso de Uso A: Retiro por el Titular (Destinatario en persona)
* **Request Body:**
```json
{
  "tipo_retiro": "TITULAR",
  "documento_presentado": {
    "tipo": "DNI",
    "numero": "40123456"
  },
  "destinatario_mayor_16": true,
  "observaciones": "Entrega realizada en ventanilla 2"
}
```

#### 📦 Caso de Uso B: Retiro por Tercero Autorizado
* **Request Body:**
```json
{
  "tipo_retiro": "TERCERO_AUTORIZADO",
  "documento_presentado": {
    "tipo": "DNI",
    "numero": "38999888"
  },
  "destinatario_mayor_16": true,
  "tercero_autorizado": {
    "nombre_completo": "Juan Pérez",
    "documento": "38999888",
    "posee_copia_dni_titular": true,
    "posee_nota_autorizacion": true
  },
  "observaciones": "Presenta nota firmada y copia de DNI en regla"
}
```

#### ✅ Respuesta Exitosa (`200 OK`):
```json
{
  "status": "success",
  "message": "Retiro del paquete registrado exitosamente en sucursal.",
  "data": {
    "paquete_id": "d476fa8c-5264-44df-a8b2-6beea61ef1b9",
    "numero_paquete": "PAQ-ZPC5LB48JJ",
    "estado": "ENTREGADO_EN_SUCURSAL",
    "tipo_retiro": "TITULAR",
    "receptor_nombre": "María López",
    "receptor_documento": "40123456",
    "es_autorizado": false,
    "usuario_administrativo_id": "c1f7b830-4e4b-4ec5-bca4-d621b764b8a2",
    "usuario_administrativo_nombre": "Laura Martínez",
    "fecha_hora_entrega": "2026-10-01T20:15:00.123456Z",
    "sucursal_id": 1,
    "observaciones": "Entrega realizada en ventanilla 2"
  }
}
```

#### ❌ Respuestas de Error:
* **`400 Bad Request` (Destinatario menor de 16 años):**
  ```json
  {
    "status": "error",
    "code": "VALIDATION_ERROR",
    "message": "No se cumplen las condiciones o requisitos documentales para el retiro.",
    "errors": [
      {
        "field": "destinatario_mayor_16",
        "message": "El titular o destinatario debe tener al menos 16 años para retirar o autorizar el retiro."
      }
    ]
  }
  ```
* **`400 Bad Request` (Tercero sin copia de DNI del titular):**
  ```json
  {
    "status": "error",
    "code": "VALIDATION_ERROR",
    "message": "No se cumplen las condiciones o requisitos documentales para el retiro.",
    "errors": [
      {
        "field": "tercero_autorizado.posee_copia_dni_titular",
        "message": "Es requisito excluyente presentar una copia física o digital del documento de identidad del destinatario titular."
      }
    ]
  }
  ```
* **`400 Bad Request` (Tercero sin nota de autorización):**
  ```json
  {
    "status": "error",
    "code": "VALIDATION_ERROR",
    "message": "No se cumplen las condiciones o requisitos documentales para el retiro.",
    "errors": [
      {
        "field": "tercero_autorizado.posee_nota_autorizacion",
        "message": "Es requisito excluyente presentar el formulario o nota de autorización de retiro firmada por el titular."
      }
    ]
  }
  ```
* **`400 Bad Request` (Paquete ya entregado previamente):**
  ```json
  {
    "status": "error",
    "code": "VALIDATION_ERROR",
    "message": "El paquete no está en un estado válido para retiro en sucursal.",
    "errors": [
      {
        "field": "estado",
        "message": "El paquete ya fue entregado o retirado previamente."
      }
    ]
  }
  ```
* **`404 Not Found` (Paquete no encontrado):**
  ```json
  {
    "status": "error",
    "code": "NOT_FOUND",
    "message": "No se encontró un paquete con el identificador 'PAQ-404'."
  }
  ```

---

## 8. Servicio de Notificación de Token por Correo (HU05)

### 8.1. Funcionamiento del Despacho Asíncrono
Al registrar un envío con éxito mediante `POST /api/v1/envios` (HU03):
1. El backend crea el registro del envío, asigna el `token_seguimiento` y los números de paquete (`numero_paquete`).
2. Se encola de inmediato una tarea en segundo plano (`BackgroundTasks`) con el servicio `ServicioNotificaciones` (`NotificationService`).
3. El endpoint responde `201 Created` al usuario sin bloquearse por la red ni depender de la latencia del proveedor de correos.
4. El servicio despacha automáticamente:
   * **Al Remitente (`remitente_email`):** Correo con el token de seguimiento, el detalle de paquetes y el enlace directo a `/seguimiento?token=...`.
   * **Al Destinatario (`destinatario_email`):** Correo informando que tiene un paquete en camino, con el token de seguimiento y el enlace para rastreo en tiempo real.
5. Cada despacho se audita en la tabla `notificaciones_envio`:
   * `canal`: `"EMAIL"`
   * `destinatario_tipo`: `"REMITENTE"` o `"DESTINATARIO"`
   * `estado`: `"ENVIADO"` o `"FALLIDO"`
   * `proveedor_mensaje_id`: Identificador devuelto por el proveedor de correo
   * `error_detalle`: Texto de error detallado en caso de fallo
6. **Tolerancia a fallos:** Si el proveedor de correo falla (error SMTP, timeout o caída de red), la creación del envío **nunca se revierte ni falla**; el error queda registrado en `notificaciones_envio` para posterior auditoría y reintento.

