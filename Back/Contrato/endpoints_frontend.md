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
9. [Endpoints de Recepción de Paquetes en Terminal (`/terminal/paquetes`) - HU06](#9-endpoints-de-recepción-de-paquetes-en-terminal-hu06)
   - `GET /api/v1/terminal/paquetes/{codigo}/escanear` (Identificar Paquete por Código de Barras)
   - `POST /api/v1/terminal/paquetes/{codigo}/recepcionar` (Registrar Recepción en la Terminal)
10. [Endpoints de Sucursales Disponibles para Retiro (`/sucursales`) - HU09](#10-endpoints-de-sucursales-disponibles-para-retiro-hu09)
    - `GET /api/v1/sucursales` (Catálogo Público con Filtros por Provincia y Ciudad)
    - `GET /api/v1/sucursales/opciones-retiro/{token}` (Opciones de Retiro de un Envío)
11. [Endpoints de Reclamos desde la Vista Pública del Token - HU07](#11-endpoints-de-reclamos-desde-la-vista-pública-del-token-hu07)
    - `GET /api/v1/reclamos/seguimiento/{token}` (Habilitar el Inicio de un Reclamo)
    - `POST /api/v1/reclamos/seguimiento/{token}` (Iniciar un Reclamo)
    - `GET|PATCH /api/v1/admin/reclamos...` (Gestión Interna)
12. [Endpoints de Preguntas Frecuentes - HU08](#12-endpoints-de-preguntas-frecuentes-hu08)
    - `GET /api/v1/preguntas-frecuentes` (Sección Pública)
    - `GET|POST|PATCH|DELETE /api/v1/admin/preguntas-frecuentes...` (Administración del Contenido)
13. [Endpoints de Recorridos de Reparto - HU10](#13-endpoints-de-recorridos-de-reparto-hu10)
    - `GET|PUT /api/v1/repartidores...` (Perfiles de Repartidor)
    - `POST /api/v1/recorridos/generar` (Generación Automática)
    - `GET /api/v1/recorridos` y `GET /api/v1/recorridos/{id}` (Visualización)
    - `PUT|DELETE /api/v1/recorridos/{id}/paquetes...`, `POST .../optimizar`, `PATCH .../repartidor`, `DELETE /api/v1/recorridos/{id}` (Edición)
    - `POST /api/v1/recorridos/{id}/iniciar` (Inicio)
    - `GET /api/v1/recorridos/alertas` y `PATCH .../alertas/{id}/resolver` (Alertas)

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
| **2** | `ADMINISTRATIVO` | Usuario administrativo operativo | Retiros (HU13), reclamos (HU07), preguntas frecuentes (HU08) y recorridos (HU10) |
| **3** | `VENDEDOR` | Personal de terminal / venta | Registro de órdenes y ventas |
| **4** | `REPARTIDOR` | Personal de reparto | Recibe recorridos (HU10); su app móvil llega con HU11/HU12 |

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


---

## 9. Endpoints de Recepción de Paquetes en Terminal (HU06)

Permite al personal de terminal autenticado con rol `VENDEDOR` (o `ADMINISTRATIVO` / `SUPERADMIN`) identificar un paquete precargado escaneando el código de barras de su planilla, y dejarlo registrado en la terminal como listo para su envío.

**Qué se escanea:** la planilla imprimible que genera HU03 lleva un código de barras **CODE128** que codifica el `numero_paquete` (formato `PAQ-XXXXXXXXXX`). Ese valor es el que va en el parámetro `{codigo}` de la URL. También se acepta el UUID del paquete.

**Normalización:** el backend limpia el valor antes de buscarlo (quita espacios, saltos de línea y el Enter final que agregan los lectores, y pasa a mayúsculas). El frontend **no** necesita sanitizar la lectura del scanner: puede mandar lo que llegó del lector tal cual, URL-encodeado.

**Flujo recomendado en pantalla:**
1. El vendedor dispara el lector → `GET .../escanear`.
2. La pantalla muestra los datos del paquete y del envío para que el vendedor los contraste con el bulto físico.
3. Si `disponible_para_recepcion` es `true`, se habilita el botón de confirmar → `POST .../recepcionar` con la sucursal.

### 9.1. Identificar Paquete por Código de Barras
Consulta de **solo lectura**: no modifica el paquete. Se puede llamar tantas veces como se escanee.

* **Método:** `GET`
* **URL:** `/api/v1/terminal/paquetes/{codigo}/escanear`
* **Parámetros de Ruta:**
  * `codigo` (string, obligatorio): valor leído del código de barras (`PAQ-XXXXXXXXXX`) o UUID del paquete.
* **Autenticación requerida:** Sí (Header `Authorization: Bearer <JWT>`)
* **Roles Permitidos:** `VENDEDOR`, `ADMINISTRATIVO`, `SUPERADMIN`

#### ✅ Respuesta Exitosa (`200 OK`) - Paquete Listo para Recibir:
```json
{
  "status": "success",
  "data": {
    "paquete_id": "d476fa8c-5264-44df-a8b2-6beea61ef1b9",
    "numero_paquete": "PAQ-ZPC5LB48JJ",
    "descripcion": "Caja con repuestos",
    "peso_kg": 4.5,
    "largo_cm": 40.0,
    "ancho_cm": 30.0,
    "alto_cm": 20.0,
    "observaciones": "Frágil",
    "estado_actual": "Pendiente",
    "disponible_para_recepcion": true,
    "motivo_no_disponible": null,
    "fecha_registro": "2026-10-12T14:03:11",
    "sucursal_actual": null,
    "envio": {
      "envio_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
      "token_seguimiento": "ENV-4KD9XM2P7Q",
      "remitente_nombre": "Carlos Pérez",
      "remitente_documento": "30111222",
      "remitente_telefono": "+543564111222",
      "destinatario_nombre": "Ana López",
      "destinatario_telefono": "+543564333444",
      "tipo_entrega": "sucursal",
      "destino": "Sucursal Rosario Sur - Bv. Oroño 2456, Rosario, Santa Fe",
      "sucursal_destino": {
        "id": 2,
        "nombre": "Sucursal Rosario Sur",
        "provincia": "Santa Fe",
        "ciudad": "Rosario",
        "direccion": "Bv. Oroño 2456",
        "latitud": -32.9587,
        "longitud": -60.6931
      }
    }
  }
}
```

> `sucursal_actual` es `null` hasta que el paquete se recibe por primera vez. `destino` ya viene armado como texto legible (domicilio completo o sucursal + dirección), con el **mismo formato** que devuelve `GET /api/v1/seguimiento/{token}` (HU04), así que la pantalla no necesita decidir el formato.
>
> **Formato de fechas:** `fecha_registro` viene de la base y se serializa sin sufijo de zona (`"2026-10-12T14:03:11"`); `fecha_hora_recepcion` (sección 9.2) la genera el backend en UTC y sí lleva `Z`.

#### ⚠️ Respuesta Exitosa (`200 OK`) - Paquete NO Disponible para Recepción:
Si el paquete ya fue recibido antes (`EN_SUCURSAL_ORIGEN`, `EN_TRANSITO`, `EN_REPARTO`, …) o ya cerró su ciclo (`ENTREGADO`, `ENTREGADO_EN_SUCURSAL`, `RETIRADO`), el escaneo **no falla**: devuelve `200` con el motivo, para que el vendedor vea en pantalla qué pasó con ese bulto.
```json
{
  "status": "success",
  "data": {
    "numero_paquete": "PAQ-ZPC5LB48JJ",
    "estado_actual": "EN_TRANSITO",
    "disponible_para_recepcion": false,
    "motivo_no_disponible": "El paquete ya fue recibido y está circulando en la red. Estado actual: 'EN_TRANSITO'.",
    "...": "resto de los campos igual que arriba"
  }
}
```

#### ❌ Respuestas de Error:
* **`400 Bad Request` (Código con formato inválido — por ejemplo, se escaneó un token `ENV-`):**
  ```json
  {
    "status": "error",
    "code": "VALIDATION_ERROR",
    "message": "El código de barras escaneado no es válido.",
    "errors": [
      {
        "field": "codigo",
        "message": "El código escaneado no tiene un formato válido. Se espera el número de paquete 'PAQ-XXXXXXXXXX' impreso en la planilla o el identificador interno del paquete."
      }
    ]
  }
  ```
* **`404 Not Found` (La planilla no corresponde a un envío registrado):**
  ```json
  {
    "status": "error",
    "code": "NOT_FOUND",
    "message": "No se encontró un paquete precargado con el código 'PAQ-NOEXISTE1'. Verificá que la planilla corresponda a un envío registrado en el sistema."
  }
  ```
* **`401 Unauthorized`:** token ausente, inválido o expirado (`INVALID_TOKEN`).
* **`403 Forbidden`:** rol no habilitado, por ejemplo `REPARTIDOR` (`FORBIDDEN_ACCESS`), o token con scope `PASSWORD_RESET_ONLY` (`FORBIDDEN_SCOPE`).

---

### 9.2. Registrar Recepción en la Terminal
Confirma la recepción física del paquete: pasa su estado a `EN_SUCURSAL_ORIGEN`, lo ubica en la sucursal indicada y deja la entrada correspondiente en el historial de estados. Todo en una sola transacción.

* **Método:** `POST`
* **URL:** `/api/v1/terminal/paquetes/{codigo}/recepcionar`
* **Parámetros de Ruta:**
  * `codigo` (string, obligatorio): mismo valor que en `escanear`.
* **Autenticación requerida:** Sí (Header `Authorization: Bearer <JWT>`)
* **Roles Permitidos:** `VENDEDOR`, `ADMINISTRATIVO`, `SUPERADMIN`
* **Headers:** `Content-Type: application/json`
* **Request Body:**
```json
{
  "sucursal_id": 1,
  "observaciones": "Caja en buen estado, sin golpes."
}
```

| Campo | Tipo | Obligatorio | Detalle |
|:---|:---|:---:|:---|
| `sucursal_id` | `int` | Sí | Terminal donde se recibe físicamente el paquete. Debe existir en `GET /api/v1/sucursales`. Debe ser mayor que 0. |
| `observaciones` | `string` o `null` | No | Observaciones del vendedor (máx. 500 caracteres). Se anexan a la observación del historial. |

#### ✅ Respuesta Exitosa (`200 OK`):
```json
{
  "status": "success",
  "message": "Paquete recibido y registrado en la terminal como listo para su envío.",
  "data": {
    "paquete_id": "d476fa8c-5264-44df-a8b2-6beea61ef1b9",
    "numero_paquete": "PAQ-ZPC5LB48JJ",
    "estado_anterior": "Pendiente",
    "estado": "EN_SUCURSAL_ORIGEN",
    "sucursal_id": 1,
    "sucursal_nombre": "Sucursal Córdoba Centro",
    "usuario_receptor_id": "b1ffcd88-7a1b-4de9-9c2e-1aa8bc471c02",
    "usuario_receptor_nombre": "Marcos Vendedor",
    "fecha_hora_recepcion": "2026-10-12T14:07:52.119Z",
    "observaciones": "Caja en buen estado, sin golpes.",
    "token_seguimiento": "ENV-4KD9XM2P7Q"
  }
}
```

> Tras esta llamada, la consulta pública de seguimiento (`GET /api/v1/seguimiento/{token}`, HU04) ya muestra el paquete en `EN_SUCURSAL_ORIGEN`.

#### ❌ Respuestas de Error:
* **`400 Bad Request` (El paquete ya fue recibido):**
  ```json
  {
    "status": "error",
    "code": "VALIDATION_ERROR",
    "message": "El paquete no se puede recibir en la terminal en su estado actual.",
    "errors": [
      {
        "field": "estado",
        "message": "El paquete ya fue recibido y está circulando en la red. Estado actual: 'EN_SUCURSAL_ORIGEN'."
      }
    ]
  }
  ```
* **`400 Bad Request` (El paquete ya fue entregado o retirado):** mismo formato, con el mensaje `"El paquete ya completó su ciclo de entrega y no puede volver a recibirse en la terminal."`.
* **`400 Bad Request` (Sucursal inexistente):**
  ```json
  {
    "status": "error",
    "code": "VALIDATION_ERROR",
    "message": "La sucursal indicada para la recepción no existe.",
    "errors": [
      { "field": "sucursal_id", "message": "No existe una sucursal con id 9999." }
    ]
  }
  ```
  En este caso el paquete **no se modifica**: se puede reintentar con la sucursal correcta.
* **`400 Bad Request` (Body inválido):** falta `sucursal_id` o es menor o igual a 0 → `VALIDATION_ERROR`.
* **`404 Not Found` / `401` / `403`:** igual que en `9.1`.

---

## 10. Endpoints de Sucursales Disponibles para Retiro (HU09)

Ambos endpoints son **públicos, sin autenticación**: forman parte de la experiencia pública, igual que la consulta de seguimiento de HU04.

### 10.1. Catálogo Público con Filtros por Provincia y Ciudad
Catálogo de sucursales de la red. Alimenta el selector de "retiro en sucursal" del formulario de registro (HU03) y la pantalla de sucursales disponibles (HU09).

* **Método:** `GET`
* **URL:** `/api/v1/sucursales`
* **Autenticación requerida:** No (Público)
* **Query Params (opcionales):**

| Param | Tipo | Detalle |
|:---|:---|:---|
| `provincia` | `string` | Filtra por provincia. Comparación sin distinguir mayúsculas y tolerante a espacios sobrantes (máx. 100 caracteres). |
| `ciudad` | `string` | Filtra por ciudad, con el mismo criterio de comparación (máx. 100 caracteres). |

> **Compatibilidad:** sin query params, el comportamiento y la forma de la respuesta son idénticos a los anteriores a HU09. El código de frontend que ya consumía este endpoint no requiere ningún cambio.

#### ✅ Respuesta Exitosa (`200 OK`):
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "nombre": "Sucursal Córdoba Centro",
      "provincia": "Córdoba",
      "ciudad": "Córdoba",
      "direccion": "Av. Colón 1234",
      "latitud": -31.4167,
      "longitud": -64.1833
    }
  ]
}
```

El resultado viene ordenado por `nombre`. Una zona sin sucursales devuelve `200` con `"data": []` — **no** un `404`.

---

### 10.2. Opciones de Retiro de un Envío
Dado el token de seguimiento de un envío, devuelve dónde se retira el paquete, si ya llegó y qué hay que llevar. Usa el mismo token que `GET /api/v1/seguimiento/{token}`, así que el usuario no necesita ningún dato nuevo.

* **Método:** `GET`
* **URL:** `/api/v1/sucursales/opciones-retiro/{token}`
* **Parámetros de Ruta:**
  * `token` (string, obligatorio): token de seguimiento del envío (`ENV-XXXXXXXXXX`).
* **Autenticación requerida:** No (Público)

#### ✅ Respuesta Exitosa (`200 OK`) - Envío para Retiro en Sucursal:
```json
{
  "status": "success",
  "data": {
    "token_seguimiento": "ENV-4KD9XM2P7Q",
    "tipo_entrega": "sucursal",
    "aplica_retiro": true,
    "motivo_no_aplica": null,
    "sucursal_asignada": {
      "id": 2,
      "nombre": "Sucursal Rosario Sur",
      "provincia": "Santa Fe",
      "ciudad": "Rosario",
      "direccion": "Bv. Oroño 2456",
      "latitud": -32.9587,
      "longitud": -60.6931,
      "es_sucursal_asignada": true
    },
    "sucursales_disponibles": [
      {
        "id": 2,
        "nombre": "Sucursal Rosario Sur",
        "provincia": "Santa Fe",
        "ciudad": "Rosario",
        "direccion": "Bv. Oroño 2456",
        "latitud": -32.9587,
        "longitud": -60.6931,
        "es_sucursal_asignada": true
      },
      {
        "id": 7,
        "nombre": "Sucursal Rosario Norte",
        "provincia": "Santa Fe",
        "ciudad": "Rosario",
        "direccion": "Av. Alberdi 1500",
        "latitud": -32.92,
        "longitud": -60.68,
        "es_sucursal_asignada": false
      }
    ],
    "paquetes": [
      {
        "numero_paquete": "PAQ-ZPC5LB48JJ",
        "descripcion": "Caja con repuestos",
        "estado": "LISTO_PARA_RETIRO",
        "disponible_para_retirar": true
      },
      {
        "numero_paquete": "PAQ-8HT3MN6RW1",
        "descripcion": "Sobre con documentación",
        "estado": "EN_TRANSITO",
        "disponible_para_retirar": false
      }
    ],
    "requisitos_retiro": {
      "titular": "Presentar documento de identidad original y acreditar ser mayor de 16 años.",
      "tercero_autorizado": "Presentar documento de identidad propio, copia del documento del titular y constancia/formulario de autorización de retiro firmada por el destinatario."
    }
  }
}
```

**Cómo interpretar la respuesta en pantalla:**

| Campo | Qué significa para la UI |
|:---|:---|
| `aplica_retiro` | Si es `false`, mostrar `motivo_no_aplica` y ocultar el resto. |
| `sucursal_asignada` | **El único lugar donde se entrega el paquete.** Es la sucursal que se eligió al registrar el envío. Destacarla. |
| `sucursales_disponibles` | La asignada viene **primero** (con `es_sucursal_asignada: true`) y después las otras de la misma ciudad, como referencia de la red cercana. Sirve para dibujarlas todas en el mapa. |
| `disponible_para_retirar` | `true` solo si el paquete ya está físicamente en la sucursal de destino (`LISTO_PARA_RETIRO`, `EN_SUCURSAL`, `EN_SUCURSAL_DESTINO`). Un paquete `Pendiente`, `EN_SUCURSAL_ORIGEN` o `EN_TRANSITO` viene en `false`: mostrar "en camino", no invitar al usuario a ir a buscarlo. |
| `requisitos_retiro` | Mismos requisitos que exige el mostrador en HU13. Mostrarlos antes de que la persona viaje. |

#### ⚠️ Respuesta Exitosa (`200 OK`) - Envío a Domicilio:
Si el envío **no** es para retiro, la respuesta sigue siendo `200`: el token es válido, simplemente ese envío se entrega en el domicilio.
```json
{
  "status": "success",
  "data": {
    "token_seguimiento": "ENV-4KD9XM2P7Q",
    "tipo_entrega": "domicilio",
    "aplica_retiro": false,
    "motivo_no_aplica": "Este envío se entrega en el domicilio del destinatario, por lo que no requiere retiro en sucursal.",
    "sucursal_asignada": null,
    "sucursales_disponibles": [],
    "paquetes": [],
    "requisitos_retiro": { "...": "textos de requisitos" }
  }
}
```

> El frontend solo tiene que mirar `aplica_retiro`: no hace falta distinguir este caso leyendo mensajes de error.

#### ❌ Respuestas de Error:
* **`404 Not Found` (Token inexistente):**
  ```json
  {
    "status": "error",
    "code": "NOT_FOUND",
    "message": "No se encontró un envío asociado a ese código de seguimiento."
  }
  ```

#### 🔒 Nota de privacidad
Como el endpoint es público, **no expone** email, teléfono ni documento del remitente o del destinatario — mismo criterio que la vista pública de HU04. Si la pantalla necesita datos de contacto, tienen que venir de un endpoint autenticado.


---

## 11. Endpoints de Reclamos desde la Vista Pública del Token (HU07)

El reclamo se inicia **sin sesión**, desde la misma vista de seguimiento de HU04, con el mismo token (`ENV-XXXXXXXXXX`). El token se acepta en minúsculas o con espacios (el backend lo normaliza). La gestión interna del reclamo es para `ADMINISTRATIVO` / `SUPERADMIN`.

**Flujo recomendado en pantalla:**
1. En la vista de seguimiento, el botón "Iniciar reclamo" llama a `GET /api/v1/reclamos/seguimiento/{token}`.
2. Si `puede_iniciar` es `true`, mostrar el formulario con `tipos_reclamo` y `paquetes`; si es `false`, mostrar `motivo_no_habilitado`.
3. Enviar con `POST` al mismo path. Mostrar la lista `reclamos` para que el usuario vea el estado y la respuesta.

### 11.1. Habilitar el Inicio de un Reclamo
* **Método:** `GET`
* **URL:** `/api/v1/reclamos/seguimiento/{token}`
* **Autenticación requerida:** No (Público)

#### ✅ Respuesta Exitosa (`200 OK`):
```json
{
  "status": "success",
  "data": {
    "token_seguimiento": "ENV-4KD9XM2P7Q",
    "puede_iniciar": true,
    "motivo_no_habilitado": null,
    "max_reclamos_activos": 5,
    "tipos_reclamo": [
      { "codigo": "DEMORA", "descripcion": "El envío está demorado o no avanza en el seguimiento." },
      { "codigo": "DANIO", "descripcion": "El paquete llegó dañado o con signos de apertura." },
      { "codigo": "EXTRAVIO", "descripcion": "El paquete se perdió o no aparece." },
      { "codigo": "OTRO", "descripcion": "Cualquier otro inconveniente relacionado con el envío." }
    ],
    "paquetes": [
      { "numero_paquete": "PAQ-ZPC5LB48JJ", "descripcion": "Caja con repuestos", "estado": "EN_REPARTO" }
    ],
    "reclamos": [
      {
        "id": "3f0c2a8e-6a4b-4d0e-9a51-7c1d2e3f4a5b",
        "numero_paquete": "PAQ-ZPC5LB48JJ",
        "tipo": "DEMORA",
        "estado": "RESUELTO",
        "descripcion": "El paquete figura en reparto desde temprano y todavía no llegó.",
        "resolucion": "El repartidor confirmó la entrega para la tarde.",
        "fecha_creacion": "2026-10-24T12:03:11",
        "ultima_actualizacion": "2026-10-24T15:40:02"
      }
    ]
  }
}
```

> `reclamos` viene del más reciente al más antiguo. **No** incluye los datos de contacto de quien reclamó (el token lo comparten remitente y destinatario).

#### ❌ Respuestas de Error:
* **`404 Not Found`:** token inexistente → `"No se encontró un envío asociado a ese código de seguimiento."`

### 11.2. Iniciar un Reclamo
* **Método:** `POST`
* **URL:** `/api/v1/reclamos/seguimiento/{token}`
* **Autenticación requerida:** No (Público)
* **Request Body:**
```json
{
  "tipo": "DEMORA",
  "descripcion": "El paquete figura en reparto desde temprano y todavía no llegó.",
  "numero_paquete": "PAQ-ZPC5LB48JJ",
  "contacto_nombre": "María Gómez",
  "contacto_email": "maria.gomez@example.com",
  "contacto_telefono": "+54 9 3564 222222"
}
```

| Campo | Tipo | Obligatorio | Detalle |
|:---|:---|:---:|:---|
| `tipo` | `string` | Sí | `DEMORA`, `DANIO`, `EXTRAVIO` u `OTRO` (no distingue mayúsculas). |
| `descripcion` | `string` | Sí | 20 a 2000 caracteres. |
| `numero_paquete` | `string` o `null` | No | Paquete afectado. Debe ser de este envío. Si se omite, el reclamo es por el envío completo. |
| `contacto_nombre` | `string` | Sí | 2 a 150 caracteres. |
| `contacto_email` | `string` o `null` | * | Email válido. |
| `contacto_telefono` | `string` o `null` | * | Dígitos, espacios, guiones, paréntesis y `+` inicial; mínimo 6 dígitos. |

\* Es obligatorio **al menos uno** de los dos medios de contacto.

#### ✅ Respuesta Exitosa (`201 Created`):
```json
{
  "status": "success",
  "message": "Reclamo registrado. Vas a poder seguir su estado con tu código de seguimiento.",
  "data": {
    "id": "3f0c2a8e-6a4b-4d0e-9a51-7c1d2e3f4a5b",
    "numero_paquete": "PAQ-ZPC5LB48JJ",
    "tipo": "DEMORA",
    "estado": "ABIERTO",
    "descripcion": "El paquete figura en reparto desde temprano y todavía no llegó.",
    "resolucion": null,
    "fecha_creacion": "2026-10-24T12:03:11",
    "ultima_actualizacion": "2026-10-24T12:03:11"
  }
}
```

#### ❌ Respuestas de Error:
* **`400 VALIDATION_ERROR`:** campos inválidos; `field: "contacto"` si no hay email ni teléfono; `field: "numero_paquete"` si el paquete no es del envío; `field: "token"` si el envío ya tiene 5 reclamos abiertos o en revisión.
* **`409 DUPLICATE_ENTRY`:** ya hay un reclamo abierto o en revisión del mismo `tipo` sobre el mismo paquete (o sobre el envío completo). Mostrar el reclamo existente de la lista `reclamos`.
* **`404 Not Found`:** token inexistente.

### 11.3. Gestión Interna de Reclamos
* **Autenticación requerida:** Sí (Bearer JWT) · **Roles:** `ADMINISTRATIVO`, `SUPERADMIN`

| Método | URL | Detalle |
|:---|:---|:---|
| `GET` | `/api/v1/admin/reclamos?estado=&tipo=&token=` | Bandeja, del más reciente al más antiguo. Filtros opcionales. Responde `{ "status", "total", "data": [...] }`. |
| `GET` | `/api/v1/admin/reclamos/{id}` | Detalle de un reclamo. |
| `PATCH` | `/api/v1/admin/reclamos/{id}/estado` | Cambio de estado. Body: `{ "estado": "RESUELTO", "resolucion": "..." }`. |

Cada reclamo de la bandeja incluye, además de lo público: `envio_id`, `token_seguimiento`, `remitente_nombre`, `destinatario_nombre`, `contacto_nombre`, `contacto_email`, `contacto_telefono`, `usuario_resolucion_id`, `usuario_resolucion_nombre`, `created_at`, `updated_at`.

**Transiciones válidas:** `ABIERTO → EN_REVISION | RESUELTO | RECHAZADO` y `EN_REVISION → RESUELTO | RECHAZADO`. Para `RESUELTO`/`RECHAZADO` la `resolucion` es obligatoria (mínimo 10 caracteres) y se muestra en la vista pública. Un reclamo cerrado no admite cambios (`400`, `field: "estado"`).

* **Errores:** `400` (filtro o transición inválida, resolución faltante), `401`, `403` (rol no habilitado o scope `PASSWORD_RESET_ONLY`), `404` (reclamo inexistente).


---

## 12. Endpoints de Preguntas Frecuentes (HU08)

### 12.1. Sección Pública de Preguntas Frecuentes
* **Método:** `GET`
* **URL:** `/api/v1/preguntas-frecuentes`
* **Autenticación requerida:** No (Público)
* **Query Params (opcionales):**

| Param | Tipo | Detalle |
|:---|:---|:---|
| `categoria` | `string` | Filtra por categoría, sin distinguir mayúsculas ni tildes (`envios` encuentra `Envíos`). Máx. 80. |
| `q` | `string` | Búsqueda libre: cada palabra debe aparecer en la pregunta, la respuesta o la categoría, sin distinguir mayúsculas ni tildes. Máx. 100. |

#### ✅ Respuesta Exitosa (`200 OK`):
```json
{
  "status": "success",
  "data": {
    "total": 2,
    "categorias": [
      { "nombre": "Envíos", "cantidad": 4 },
      { "nombre": "Seguimiento", "cantidad": 3 },
      { "nombre": "Retiro en sucursal", "cantidad": 2 },
      { "nombre": "Entregas a domicilio", "cantidad": 2 },
      { "nombre": "Reclamos", "cantidad": 2 }
    ],
    "preguntas": [
      {
        "id": 12,
        "categoria": "Reclamos",
        "pregunta": "¿Cómo inicio un reclamo?",
        "respuesta": "Consultá tu envío con el código de seguimiento y elegí la opción para iniciar un reclamo...",
        "orden": 120
      }
    ]
  }
}
```

**Cómo usarlo en pantalla:** `categorias` trae **todas** las categorías publicadas aunque se haya filtrado (sirve para los chips o pestañas de filtro); `preguntas` y `total` respetan los filtros. Las preguntas vienen ya ordenadas; para agruparlas, usar `categoria` (nunca viene vacía: las que no tienen se muestran como `"General"`). Sin resultados responde `200` con `"preguntas": []`.

### 12.2. Administración del Contenido
* **Autenticación requerida:** Sí (Bearer JWT) · **Roles:** `ADMINISTRATIVO`, `SUPERADMIN`

| Método | URL | Detalle |
|:---|:---|:---|
| `GET` | `/api/v1/admin/preguntas-frecuentes` | Todas, incluidas las no publicadas. |
| `GET` | `/api/v1/admin/preguntas-frecuentes/{id}` | Detalle. |
| `POST` | `/api/v1/admin/preguntas-frecuentes` | Alta (`201`). |
| `PATCH` | `/api/v1/admin/preguntas-frecuentes/{id}` | Modificación parcial: solo los campos enviados. `"categoria": null` la quita. |
| `DELETE` | `/api/v1/admin/preguntas-frecuentes/{id}` | Baja. Para ocultar sin borrar, `PATCH` con `publicada: false`. |

Body de alta:
```json
{
  "categoria": "Pagos",
  "pregunta": "¿Qué medios de pago aceptan?",
  "respuesta": "Efectivo y tarjetas de débito o crédito en sucursal.",
  "orden": 140,
  "publicada": true
}
```

| Campo | Tipo | Obligatorio | Detalle |
|:---|:---|:---:|:---|
| `categoria` | `string` o `null` | No | Máx. 80. Se recortan espacios. |
| `pregunta` | `string` | Sí | 5 a 255. |
| `respuesta` | `string` | Sí | 10 a 5000. |
| `orden` | `int` | No | 0 a 10000 (default 0). Menor = primero. |
| `publicada` | `bool` | No | Default `true`. |

Respuesta (alta, detalle y modificación):
```json
{
  "status": "success",
  "message": "Pregunta frecuente creada correctamente.",
  "data": {
    "id": 14,
    "categoria": "Pagos",
    "pregunta": "¿Qué medios de pago aceptan?",
    "respuesta": "Efectivo y tarjetas de débito o crédito en sucursal.",
    "orden": 140,
    "publicada": true,
    "created_at": "2026-10-24T12:00:00",
    "updated_at": "2026-10-24T12:00:00"
  }
}
```

* **Errores:** `400` (validación; body vacío en `PATCH`), `409 DUPLICATE_ENTRY` (la pregunta ya existe, aunque difiera en tildes o signos), `404` (id inexistente), `401`, `403`.


---

## 13. Endpoints de Recorridos de Reparto (HU10)

Todos requieren **Bearer JWT** con rol `ADMINISTRATIVO` o `SUPERADMIN` (personal de logística). `VENDEDOR` y `REPARTIDOR` reciben `403 FORBIDDEN_ACCESS`; un token `PASSWORD_RESET_ONLY`, `403 FORBIDDEN_SCOPE`.

**Flujo recomendado en pantalla:**
1. Configurar una vez a cada repartidor (13.1).
2. Elegir sucursal, tipo (`CORTA`/`LARGA`) y fecha → generar (13.2). Mostrar los recorridos en el mapa y las `alertas`.
3. Revisar/editar cada recorrido (13.4). Mostrar las `alertas` que devuelve cada edición.
4. Iniciar el recorrido cuando sale el repartidor (13.5).

### 13.1. Perfiles de Repartidor
| Método | URL | Detalle |
|:---|:---|:---|
| `GET` | `/api/v1/repartidores?sucursal_id=&tipo_reparto=&activo=` | Usuarios con rol REPARTIDOR. Con filtros, solo los que tienen perfil. |
| `GET` | `/api/v1/repartidores/{usuario_id}` | Detalle. |
| `PUT` | `/api/v1/repartidores/{usuario_id}/perfil` | Crea o reemplaza el perfil. |

Body del `PUT`:
```json
{ "sucursal_base_id": 1, "tipo_reparto": "CORTA", "activo": true }
```

Respuesta (`200`):
```json
{
  "status": "success",
  "message": "Perfil de repartidor creado.",
  "data": {
    "usuario_id": "7c53315c-a2d8-4b54-936d-1e12bcf9b1c5",
    "nombre": "Diego Repartidor",
    "dni": "37222333",
    "email": "diego.repartidor@empresa.com",
    "telefono": "+543564222333",
    "estado_usuario": "Activo",
    "perfil_configurado": true,
    "sucursal_base": { "id": 1, "nombre": "Sucursal Córdoba Centro", "provincia": "Córdoba", "ciudad": "Córdoba", "direccion": "Av. Colón 1234", "latitud": -31.4167, "longitud": -64.1833 },
    "tipo_reparto": "CORTA",
    "activo": true,
    "disponible_para_recorridos": true
  }
}
```

* **Errores:** `400` (tipo inválido, sucursal inexistente, el usuario no es REPARTIDOR), `404` (usuario inexistente), `409` (tiene recorridos activos y se intenta cambiar sucursal, tipo o desactivarlo).

### 13.2. Generar Recorridos Automáticamente
* **Método:** `POST`
* **URL:** `/api/v1/recorridos/generar`
* **Request Body:**
```json
{
  "sucursal_id": 1,
  "tipo_distancia": "CORTA",
  "fecha": "2026-10-24",
  "orientacion_calles_grados": 20,
  "repartidor_ids": null,
  "reemplazar_existentes": false
}
```

| Campo | Tipo | Obligatorio | Detalle |
|:---|:---|:---:|:---|
| `sucursal_id` | `int` | Sí | Sucursal de partida. Debe tener coordenadas. |
| `tipo_distancia` | `string` | Sí | `CORTA`: entregas a domicilio en la ciudad. `LARGA`: traslados a otras sucursales. |
| `fecha` | `date` | No | Default: hoy. |
| `orientacion_calles_grados` | `float` | No | Desde 0 y menor que 90. Ángulo de la cuadrícula de calles respecto del norte; solo afecta a `CORTA`. Default `0`. |
| `repartidor_ids` | `uuid[]` | No | Subconjunto de repartidores. Default: todos los disponibles de la sucursal y el tipo sin otro recorrido activo ese día. |
| `reemplazar_existentes` | `bool` | No | Si ya hay recorridos sin iniciar para esa sucursal/fecha/tipo, los descarta y genera de nuevo. Sin esto, `409`. |

#### ✅ Respuesta Exitosa (`200 OK`):
```json
{
  "status": "success",
  "message": "Se generaron 2 recorrido(s) con 6 paquete(s). 1 paquete(s) quedaron sin recorrido: revisá las alertas.",
  "data": {
    "sucursal_id": 1,
    "fecha": "2026-10-24",
    "tipo_distancia": "CORTA",
    "orientacion_calles_grados": 20.0,
    "resumen": {
      "paquetes_pendientes": 7,
      "paquetes_asignados": 6,
      "paquetes_sin_recorrido": 1,
      "repartidores_disponibles": 2,
      "recorridos_generados": 2,
      "recorridos_reemplazados": 0
    },
    "recorridos": [ { "...": "mismo formato que el detalle de 13.3" } ],
    "alertas": [
      {
        "id": "b1e6c0d4-...",
        "paquete_id": "d476fa8c-...",
        "numero_paquete": "PAQ-8HT3MN6RW1",
        "token_seguimiento": "ENV-4KD9XM2P7Q",
        "destino": "Colón 900, Córdoba, Córdoba",
        "motivo": "SIN_UBICACION_DESTINO",
        "descripcion_motivo": "El destino no tiene coordenadas: no se puede ubicar en el mapa y debe asignarse manualmente.",
        "sucursal_actual_id": 1,
        "recorrido_id": null,
        "resuelta": false,
        "created_at": "2026-10-24T09:15:39",
        "resuelta_at": null
      }
    ]
  }
}
```

**Motivos de alerta:** `SIN_UBICACION_DESTINO`, `SIN_SUCURSAL_DESTINO`, `SIN_REPARTIDOR_DISPONIBLE`, `SIN_RECORRIDO_ASIGNADO`. Mostrar `descripcion_motivo`. Sin paquetes pendientes la respuesta es `200` con `recorridos: []`.

* **Errores:** `400` (sucursal inexistente o sin coordenadas, tipo inválido, orientación fuera de rango, `repartidor_ids[i]` no disponible), `409 DUPLICATE_ENTRY` (ya hay recorridos sin iniciar: reenviar con `reemplazar_existentes: true`).

### 13.3. Visualizar Recorridos
| Método | URL | Detalle |
|:---|:---|:---|
| `GET` | `/api/v1/recorridos?sucursal_id=&fecha=&tipo_distancia=&estado=&repartidor_id=` | Resumen. `{ "status", "total", "data": [...] }`. |
| `GET` | `/api/v1/recorridos/{id}` | Detalle para el mapa. `{ "status", "message", "data", "alertas" }`. |

Detalle (`data`):
```json
{
  "id": "0b8f1c2e-...",
  "fecha": "2026-10-24",
  "tipo_distancia": "CORTA",
  "estado": "GENERADO",
  "generado_automaticamente": true,
  "sucursal_origen_id": 1,
  "sucursal_origen_nombre": "Sucursal Córdoba Centro",
  "repartidor": { "usuario_id": "7c53315c-...", "nombre": "Diego Repartidor", "telefono": "+543564222333" },
  "cantidad_paradas": 1,
  "cantidad_paquetes": 1,
  "distancia_estimada_km": 1.62,
  "duracion_estimada_min": 9,
  "created_at": "2026-10-24T09:16:20",
  "updated_at": "2026-10-24T09:16:20",
  "orientacion_calles_grados": 20.0,
  "vuelve_a_sucursal": true,
  "sucursal_origen": { "id": 1, "nombre": "Sucursal Córdoba Centro", "provincia": "Córdoba", "ciudad": "Córdoba", "direccion": "Av. Colón 1234", "latitud": -31.4167, "longitud": -64.1833 },
  "paradas": [
    {
      "orden": 1,
      "tipo_parada": "DOMICILIO",
      "destino": "San Martín 100, Córdoba, Córdoba",
      "latitud": -31.41,
      "longitud": -64.19,
      "sucursal_destino": null,
      "paquetes": [
        {
          "paquete_id": "d476fa8c-...",
          "numero_paquete": "PAQ-ZPC5LB48JJ",
          "orden": 1,
          "descripcion": "Libros",
          "peso_kg": 3.0,
          "estado": "EN_SUCURSAL_ORIGEN",
          "estado_en_recorrido": "PENDIENTE",
          "token_seguimiento": "ENV-4KD9XM2P7Q",
          "destinatario_nombre": "María Gómez",
          "destinatario_telefono": "+543564222222"
        }
      ]
    }
  ],
  "trazado": [
    { "latitud": -31.4167, "longitud": -64.1833 },
    { "latitud": -31.41, "longitud": -64.19 },
    { "latitud": -31.4167, "longitud": -64.1833 }
  ],
  "paquetes_sin_ubicacion": 0
}
```

**Cómo dibujarlo:** `trazado` es la polilínea en orden de visita (sucursal, paradas y vuelta a la sucursal si `vuelve_a_sucursal`). En `LARGA`, `tipo_parada` es `SUCURSAL`, `sucursal_destino` viene poblado y no hay vuelta. Una parada con `latitud: null` es un domicilio sin coordenadas agregado a mano: listarla, pero no tiene punto en el mapa.

### 13.4. Editar un Recorrido (solo `GENERADO` o `EN_EDICION`)
| Método | URL | Body | Detalle |
|:---|:---|:---|:---|
| `PUT` | `/api/v1/recorridos/{id}/paquetes` | `{ "paquetes": ["PAQ-...", "PAQ-..."] }` | Lista completa en orden de visita (números o UUID). Agrega, quita y reordena. |
| `DELETE` | `/api/v1/recorridos/{id}/paquetes/{codigo}` | — | Quita un paquete. No se puede quitar el último. |
| `PATCH` | `/api/v1/recorridos/{id}/paquetes/{codigo}/ubicacion` | `{ "latitud": -34.58, "longitud": -58.42 }` | Completa un domicilio sin coordenadas en corta distancia. Guarda el punto en el envío y recalcula sus recorridos editables conservando el orden. |
| `POST` | `/api/v1/recorridos/{id}/optimizar` | — | Recalcula el mejor orden de los paquetes actuales. |
| `PATCH` | `/api/v1/recorridos/{id}/repartidor` | `{ "repartidor_id": "uuid" }` | Reasigna a otro repartidor disponible de la misma sucursal y tipo. |
| `DELETE` | `/api/v1/recorridos/{id}` | — | Descarta el recorrido; sus paquetes quedan libres (y se alertan). Responde `{ "status", "message", "alertas" }`. |

Todas salvo eliminar el recorrido devuelven el detalle actualizado (formato 13.3) y `alertas` con los paquetes de la sucursal que siguen sin recorrido de ese tipo. Una edición manual deja el recorrido en `EN_EDICION` con `generado_automaticamente: false`.

**Completar ubicación:** admite latitudes entre -90 y 90 y longitudes entre -180 y 180, ambas finitas y obligatorias. La ubicación se comparte entre todos los paquetes del envío. Devuelve `400` si el punto cambia el tipo de reparto de un recorrido afectado o el recorrido no es editable; `404` si el paquete no pertenece al recorrido; `409` si el domicilio ya tiene coordenadas o alguno de sus recorridos activos está en curso. La interfaz permite seleccionar el punto en el mapa o ingresarlo por teclado, sin asumir que la sucursal de partida sea el destino.

* **Errores:** `400` con `field: "paquetes[i]"` por cada paquete inválido (inexistente, repetido, en otra sucursal, no listo, en otro recorrido activo o de otro tipo de reparto); `400` con `field: "estado"` si el recorrido ya no es editable; `404` (recorrido inexistente o paquete que no forma parte del recorrido); `409` (el repartidor ya tiene otro recorrido activo ese día).

### 13.5. Iniciar un Recorrido
* **Método:** `POST`
* **URL:** `/api/v1/recorridos/{id}/iniciar`

Pasa el recorrido a `EN_CURSO` y cada paquete a `EN_REPARTO` (`CORTA`) o `EN_TRANSITO` (`LARGA`), visible enseguida en `GET /api/v1/seguimiento/{token}`. Desde ahí no se edita ni se elimina.

* **Errores:** `400` (no está `GENERADO`/`EN_EDICION`, no tiene paquetes, o algún paquete ya no está listo en la sucursal: quitarlo antes).

### 13.6. Alertas de Paquetes sin Recorrido
| Método | URL | Detalle |
|:---|:---|:---|
| `GET` | `/api/v1/recorridos/alertas?sucursal_id=&incluir_resueltas=false` | Alertas pendientes (o todas). `{ "status", "total", "data": [...] }`. |
| `PATCH` | `/api/v1/recorridos/alertas/{id}/resolver` | Marca como resuelta una alerta atendida por fuera del sistema. `400` si ya estaba resuelta. |

Las alertas también se resuelven solas cuando el paquete entra en un recorrido o sale de la sucursal.
