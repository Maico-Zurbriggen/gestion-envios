# Documentación técnica del backend

Esta carpeta documenta, en detalle, lo que efectivamente se construyó en `Back/` a medida que avanza el Sprint 1 (HU01–HU04). Es documentación de implementación, pensada para cualquiera del equipo que necesite entender **cómo funciona el backend por dentro** — no solo qué endpoints expone.

Se complementa con otras dos carpetas del repositorio, que tienen un propósito distinto:

- [`Back/Contexto/`](../Contexto/) guarda los documentos de especificación originales que se usaron como prompt para generar el backend (útiles como historial de decisiones, pero no siempre reflejan el estado final del código).
- [`knowledge/`](../../knowledge/) (en la raíz del repo) documenta contratos de API pensados para el consumo desde el frontend — el "qué" de cada endpoint, en un formato breve.

Esta carpeta (`Back/docs/`) es el "cómo y por qué" del lado del backend: arquitectura interna, modelo de datos, seguridad, reglas de negocio y estrategia de testing.

## Índice

### 1. Arquitectura
- [Capas y estructura del proyecto](./01-arquitectura/capas-y-estructura.md)
- [Modelo de datos](./01-arquitectura/modelo-de-datos.md)

### 2. Configuración
- [Desarrollo local](./02-configuracion/desarrollo-local.md)
- [Variables de entorno](./02-configuracion/variables-de-entorno.md)

### 3. Seguridad
- [Autenticación y autorización (JWT, scopes, roles)](./03-seguridad/autenticacion-jwt.md)
- [Manejo estándar de errores](./03-seguridad/manejo-de-errores.md)

### 4. Historias de usuario implementadas
- [HU01 — Alta de empleados por Superadministrador](./04-historias-de-usuario/hu01-alta-empleados.md)
- [HU02 — Primer acceso y cambio obligatorio de contraseña](./04-historias-de-usuario/hu02-primer-acceso.md)
- [HU03 — Registro de envíos](./04-historias-de-usuario/hu03-registro-envios.md)
- [HU04 — Seguimiento público por token](./04-historias-de-usuario/hu04-seguimiento-publico.md)

### 5. Testing
- [Estrategia de pruebas](./05-testing/estrategia-de-pruebas.md)

## Cómo mantener esta carpeta

- Cada vez que se implemente o modifique una historia de usuario en el backend, actualizar el documento correspondiente en `04-historias-de-usuario/` (o crear uno nuevo si es una HU distinta).
- Si cambia una decisión transversal (capas, modelo de datos, seguridad, manejo de errores), actualizar el documento de la sección correspondiente en el mismo commit que el código.
- Los ejemplos de request/response de cada documento deben poder verificarse contra Swagger (`/docs`) en un backend recién levantado.