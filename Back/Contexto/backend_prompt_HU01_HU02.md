# Especificación Técnica de Requerimientos Backend (Sprint 1: HU01 y HU02)

**Proyecto:** Sistema de Gestión de Envíos y Distribución  
**Materia:** Ingeniería y Calidad de Software  
**Ciclo Lectivo:** 2026  
**Integrantes:** Calatroni Gerónimo, Macello Agustín, Patat Agustín, Zurbriggen Maico  
**Docentes:** Diego Gabino | Saldarini Javier Daniel  
**Destinatario:** Antigravity IDE (Agente de Desarrollo Backend)  

---

## 1. Contexto y Objetivo
El objetivo de este documento es definir de forma rigurosa, exhaustiva y profesional la arquitectura, modelos de datos, endpoints API REST, reglas de negocio y criterios de aceptación para la implementación exclusiva del **Backend** correspondiente a las Historias de Usuario **HU01** y **HU02** del Sprint 1.

Este documento servirá como directiva técnica de desarrollo para **Antigravity IDE**, estableciendo las pautas necesarias para estructurar la capa de datos, la capa de servicios, las validaciones del servidor y la seguridad de autenticación.

---

## 2. Alcance del Desarrollo Backend (Sprint 1 - HU01 & HU02)

| HU | Título | Tareas Backend Extraídas de la Pila de Sprint | Horas Estimadas | Prioridad |
|---|---|---|---|---|
| **HU01** | Gestión de Empleados por Superadministrador | • Autenticación de Superadmin con credenciales precargadas<br>• Endpoint de creación de empleado con validaciones en servidor<br>• Generación automática de contraseña temporal<br>• Asignación automática del estado inicial 'Activo' | 19.0 h | Alta |
| **HU02** | Primer Acceso de Usuario Administrativo | • Validación de credenciales (DNI + contraseña temporal)<br>• Detección de primer acceso y flujo de redirección/flag obligatorio<br>• Endpoint de cambio de contraseña obligatoria y almacenamiento seguro<br>• Flujo y autorización para accesos posteriores con nueva contraseña | 18.0 h | Alta |

*Nota: Se excluyen explícitamente todas las tareas concernientes a interfaces gráficas (Frontend), pruebas manuales de UI y actividades generales de equipo.*

---

## 3. Historias de Usuario y Criterios de Aceptación (BDD)

### HU01 - Superadministrador: Iniciar sesión y gestionar el alta de empleados administrativos
**Descripción:** Yo como Superadministrador deseo iniciar sesión y gestionar el alta de empleados administrativos para habilitar y mantener usuarios administrativos que puedan operar el sistema.

* **Escenario 1: Inicio de sesión exitoso del Superadministrador**
  * **DADO** que el Superadministrador dispone de credenciales precargadas definidas para el sistema.
  * **CUANDO** envía una solicitud de autenticación con las credenciales correctas.
  * **ENTONCES** el backend valida el acceso, genera un token de sesión seguro (JWT) con rol `SUPERADMIN` y habilita el acceso a los endpoints administrativos.
* **Escenario 2: Credenciales incorrectas**
  * **CUANDO** se envían credenciales que no coinciden con las registradas.
  * **ENTONCES** el backend rechaza la operación devolviendo un código `401 Unauthorized` y un mensaje de error estandarizado.
* **Escenario 3: Alta de empleado válida**
  * **CUANDO** el Superadministrador envía un payload con `nombre`, `DNI`, `email`, `teléfono` y `rol` con datos válidos.
  * **ENTONCES** el servidor valida los datos, verifica unicidad (DNI y Email), crea el registro en la base de datos, genera automáticamente una contraseña temporal alfanumérica, asigna el estado inicial `Activo`, establece el flag `requiere_cambio_password = True` y retorna la entidad creada junto a la clave temporal.
* **Escenario 4: Datos inválidos o duplicados**
  * **CUANDO** el payload contiene datos formalmente inválidos o un DNI/Email previamente registrado.
  * **ENTONCES** el servidor rechaza la transacción con código `400 Bad Request` o `409 Conflict`, detallando los errores de validación.

---

### HU02 - Usuario Administrativo: Primer acceso y cambio obligatorio de contraseña
**Descripción:** Yo como Usuario Administrativo deseo realizar mi primer acceso con DNI y contraseña temporal y cambiar obligatoriamente la contraseña para comenzar a utilizar el sistema con credenciales propias.

* **Escenario 1: Primer acceso válido**
  * **DADO** que el usuario administrativo fue creado y posee una contraseña temporal asignada.
  * **CUANDO** solicita autenticación indicando su `DNI` y contraseña temporal.
  * **ENTONCES** el backend autentica las credenciales, detecta que `requiere_cambio_password == True` y responde indicando el estado de cambio obligatorio de clave, emitiendo un token temporal restringido únicamente al endpoint de cambio de clave.
* **Escenario 2: Cambio de contraseña exitoso**
  * **CUANDO** el usuario envía la nueva contraseña y su confirmación cumpliendo con las políticas de seguridad (longitud mínima, caracteres complejos).
  * **ENTONCES** el backend hashea la nueva contraseña con un algoritmo seguro (e.g., Argon2id o BCrypt), actualiza el hash en la base de datos, establece `requiere_cambio_password = False` y retorna una confirmación exitosa con un JWT con permisos operativos completos.
* **Escenario 3: Cambio de contraseña inválido**
  * **CUANDO** la nueva contraseña no cumple con las reglas de complejidad o la confirmación no coincide.
  * **ENTONCES** el backend rechaza la solicitud (`400 Bad Request`) explicando las reglas de la política de contraseñas.
* **Escenario 4: Accesos posteriores**
  * **DADO** que el usuario ya realizó el cambio de contraseña previamente (`requiere_cambio_password == False`).
  * **CUANDO** inicia sesión con su DNI y nueva contraseña.
  * **ENTONCES** el servidor valida el hash de la contraseña, otorga el token JWT estándar y permite el acceso normal al sistema sin forzar el cambio.

---

## 4. Arquitectura del Modelo de Datos (Esquema SQL)

A continuación se define el esquema relacional requerido para dar soporte a HU01 y HU02.

```sql
-- TABLA DE ROLES
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE NOT NULL, -- 'SUPERADMIN', 'ADMINISTRATIVO', 'VENDEDOR', 'REPARTIDOR'
    descripcion VARCHAR(255)
);

-- TABLA DE USUARIOS / EMPLEADOS
CREATE TABLE usuarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre VARCHAR(100) NOT NULL,
    dni VARCHAR(20) UNIQUE NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    telefono VARCHAR(30) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'Activo', -- 'Activo', 'Inactivo', 'Bloqueado'
    requiere_cambio_password BOOLEAN NOT NULL DEFAULT TRUE,
    rol_id INT NOT NULL REFERENCES roles(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- INDICES RECOMENDADOS PARA RENDIMIENTO
CREATE INDEX idx_usuarios_dni ON usuarios(dni);
CREATE INDEX idx_usuarios_email ON usuarios(email);
```

---

## 5. Especificación de Endpoints API REST

### 5.1. Autenticación de Superadministrador / Login General
* **Endpoint:** `POST /api/v1/auth/login`
* **Acceso:** Público
* **Payload de entrada (`Request Body`):**
  ```json
  {
    "dni": "12345678",
    "password": "PasswordTemporal123!"
  }
  ```
* **Respuestas esperadas:**
  * `200 OK` (Login Normal - Acceso otorgado):
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
  * `200 OK` (Primer Acceso Requerido - Pauta HU02):
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
  * `401 Unauthorized`:
    ```json
    {
      "status": "error",
      "code": "AUTH_FAILED",
      "message": "Credenciales inválidas."
    }
    ```

---

### 5.2. Alta de Empleado Administrativo (HU01)
* **Endpoint:** `POST /api/v1/admin/empleados`
* **Acceso:** Requerido Token JWT con rol `SUPERADMIN`.
* **Payload de entrada:**
  ```json
  {
    "nombre": "Carlos Gómez",
    "dni": "35123456",
    "email": "carlos.gomez@empresa.com",
    "telefono": "+543564123456",
    "rol_id": 2
  }
  ```
* **Lógica Interna / Procesamiento:**
  1. Validar formato de DNI (solo dígitos), Email válido y Teléfono.
  2. Verificar que no exista otro usuario con mismo `dni` o `email`.
  3. Generar contraseña temporal segura (8-12 caracteres alfanuméricos con mayúsculas, minúsculas y símbolos).
  4. Generar `password_hash` utilizando algoritmo seguro (BCrypt / Argon2).
  5. Insertar registro con `estado = 'Activo'` y `requiere_cambio_password = true`.
* **Respuestas esperadas:**
  * `201 Created`:
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
        "password_temporal": "Tmp#9284Kz"
      }
    }
    ```
  * `400 Bad Request`: Formato de entrada inválido.
  * `409 Conflict`: DNI o Email ya se encuentran registrados.

---

### 5.3. Cambio Obligatorio de Contraseña (HU02)
* **Endpoint:** `POST /api/v1/auth/cambiar-password`
* **Acceso:** Requerido Token JWT (o `temp_token` de primer acceso).
* **Payload de entrada:**
  ```json
  {
    "password_actual": "Tmp#9284Kz",
    "nueva_password": "MiNuevaPasswordSegura2026!",
    "confirmacion_password": "MiNuevaPasswordSegura2026!"
  }
  ```
* **Lógica Interna / Procesamiento:**
  1. Validar que `nueva_password` y `confirmacion_password` coincidan exactamente.
  2. Validar políticas de seguridad de la nueva clave (mínimo 8 caracteres, al menos 1 mayúscula, 1 número y 1 carácter especial).
  3. Verificar que la `password_actual` sea correcta contra el hash guardado.
  4. Hashear la nueva contraseña e implemetar el UPDATE en BD setting `requiere_cambio_password = false`.
* **Respuestas esperadas:**
  * `200 OK`:
    ```json
    {
      "status": "success",
      "message": "Contraseña actualizada exitosamente. Ya puede operar normalmente.",
      "data": {
        "auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
      }
    }
    ```
  * `400 Bad Request`: Las contraseñas no coinciden o no cumplen con los requisitos de seguridad.

---

## 6. Reglas de Negocio y Seguridad Servidor

1. **Hash de Contraseñas:** Queda estrictamente prohibido guardar o procesar contraseñas en texto plano. Se debe aplicar BCrypt (salting factor >= 10) o Argon2.
2. **Generación de Contraseñas Temporales:** Deben cumplir la expresión regular de complejidad básica y ser generadas mediante un PRNG (Pseudo-Random Number Generator) criptográficamente seguro.
3. **Manejo de Sesiones (JWT):**
   * El token emitido durante el primer acceso (cuando `requiere_cambio_password == true`) debe contener un claim de alcance restringido (ejemplo: `scope: "PASSWORD_RESET_ONLY"`), bloqueando el acceso a otros endpoints operacionales del sistema.
   * Tras efectuar el cambio de clave exitoso, se invalida el scope restringido y se otorga el JWT con permisos plenos (`scope: "FULL_ACCESS"`).
4. **Validaciones Estrictas (Middleware):**
   * Sanetización y validación de tipos de datos en la capa de entrada (DTOs / Request Validators).
   * Respuestas estructuradas uniformemente en formato JSON para simplificar el consumo desde el cliente.

---

## 7. Instrucciones Directas para Antigravity IDE
* **Paso 1:** Crea los modelos ORM / tablas SQL indicadas en la sección 4.
* **Paso 2:** Implementa los controladores/rutas para `/auth/login`, `/admin/empleados` y `/auth/cambiar-password`.
* **Paso 3:** Asegura que los middleware de autenticación y autorización (roles) validen correctamente las políticas del primer acceso y los tokens JWT.
* **Paso 4:** Expon las respuestas JSON con la estructura detallada en este documento.
