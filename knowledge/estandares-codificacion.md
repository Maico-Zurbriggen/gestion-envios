# Estándares y buenas prácticas de codificación del sistema de gestión de envíos

## 1. Tecnologías y organización del proyecto

### 1.1. Tecnologías comprobadas

Las versiones indicadas corresponden a los rangos declarados, no a una auditoría de versiones instaladas.

| Área | Tecnologías y función |
|---|---|
| Frontend | TypeScript, React 19 y Vite 8; componentes funcionales y compilación de la aplicación web.
| Navegación y estado | React Router 7; Redux Toolkit 2 con React Redux; TanStack Query 5 para consultas y mutaciones remotas.
| Interfaz y documentos | CSS, `lucide-react`, Leaflet, JsBarcode y jsPDF para estilos, iconos, mapas, códigos de barras y etiquetas PDF.
| Backend | Python 3.12 o superior, FastAPI y Uvicorn; contratos Pydantic v2 y configuración con pydantic-settings.
| Persistencia | SQLAlchemy 2 asíncrono, Alembic y drivers `aiosqlite` y `asyncpg`. La URL predeterminada usa SQLite; PostgreSQL dispone de driver declarado, sin que esto pruebe un despliegue efectivo.
| Autenticación y trazabilidad | PyJWT, bcrypt, logging y middleware de identificador de correlación.
| Calidad y pruebas | ESLint, TypeScript, Ruff, import-linter, pytest, pytest-asyncio y HTTPX. Su alcance concreto se describe en 3.1.

### 1.2. Estructura y responsabilidades

```text
gestion-envios/
├── front/src/
│   ├── app/                 Store y configuración de navegación
│   ├── features/
│   │   ├── auth/            Sesión y cambio de contraseña
│   │   ├── home/            Inicio y accesos
│   │   ├── users/           Alta de empleados
│   │   ├── shipments/       Registro, sucursales, mapas y etiquetas
│   │   ├── tracking/        Seguimiento público
│   │   └── pickup/          Retiro en sucursal
│   ├── router/              Rutas públicas, privadas y protección
│   ├── layouts/             Estructura visual compartida
│   ├── shared/              Tema y hooks transversales
│   └── styles/              Tokens y estilos comunes
├── Back/
│   ├── app/
│   │   ├── api/             Routers, dependencias y manejadores HTTP
│   │   ├── application/     Servicios e interfaces
│   │   ├── contracts/       Modelos de entrada y salida Pydantic
│   │   ├── domain/          Reglas, constantes y entidades declaradas
│   │   ├── infrastructure/  Persistencia, JWT, hashing y correo
│   │   └── core/            Configuración, excepciones y logging
│   └── tests/               Pruebas unitarias, de integración y arquitectura
└── knowledge/               Documentación compartida
```

El frontend se organiza por funcionalidad: las páginas, hooks, servicios y tipos propios de cada dominio permanecen juntos. Los componentes coordinan la presentación y eventos; los hooks integran estado y operaciones remotas; los servicios realizan solicitudes HTTP y transforman sus datos.

El backend presenta una separación por capas con servicios de aplicación, interfaces y repositorios. Los routers cumplen el papel de controladores HTTP. El flujo representativo de alta de empleados es:

```text
CreateUserPage → useCreateUser → usersApi.createUser
    → router admin.crear_empleado → ServicioEmpleados
    → IRepositorioUsuarios / RepositorioUsuarios → AsyncSession
```

**Alcance arquitectónico real:** existen puertos definidos mediante `Protocol` y composición con `Depends`, pero la inversión de dependencias no es completa. `ServicioEmpleados` importa `UsuarioModel` y `HasherContrasenas`; `ServicioEnvios` importa modelos ORM. Además, la dataclase `Usuario` declara expresamente que los servicios trabajan con el modelo SQLAlchemy. Por ello, corresponde describir una arquitectura por capas con interfaces y acoplamientos a infraestructura, sin afirmar independencia estricta del ORM ni una implementación completa de Clean Architecture. Evidencia: [ServicioEmpleados](../Back/app/application/services/servicio_empleados.py), [ServicioEnvios](../Back/app/application/services/servicio_envios.py), [Usuario](../Back/app/domain/entities/usuario.py).

## 2. Estándares y buenas prácticas de codificación aplicados

### 2.1. Criterios generales

#### G1. Nomenclatura según lenguaje y responsabilidad — recurrente

- **Descripción:** utilizar nombres que permitan reconocer el tipo de elemento y su función.
- **Implementación:** componentes, interfaces y clases usan PascalCase (`CreateUserPage`, `AuthSession`, `ServicioEmpleados`); funciones y variables TypeScript usan camelCase (`createUser`, `roleId`); módulos, funciones y variables Python usan snake_case (`servicio_empleados.py`, `crear_empleado`). Los hooks comienzan con `use` y las constantes usan mayúsculas con guiones bajos. Los nombres frontend son predominantemente ingleses y los de negocio backend, españoles; no se observa un idioma único para todo el monorepo.
- **Justificación:** facilita localizar elementos y reconocer su responsabilidad sin leer toda su implementación.

#### G2. Modularidad por responsabilidad — recurrente

- **Descripción:** agrupar elementos relacionados y separar presentación, coordinación y acceso a datos.
- **Implementación:** las features frontend repiten las carpetas `pages`, `hooks`, `services` y `types` según sus necesidades. En backend se separan routers, servicios, contratos, reglas y repositorios. Las funciones de validación y los servicios se importan desde los módulos consumidores.
- **Justificación:** delimita el lugar de cada cambio y reduce la dispersión de responsabilidades.

#### G3. Configuración de aplicaciones separada de sus consumidores — recurrente, con alcance limitado

- **Descripción:** obtener parámetros variables desde mecanismos de configuración reconocibles.
- **Implementación:** los servicios que consumen la API propia leen `import.meta.env.VITE_API_URL` y eliminan barras finales. El backend agrupa parámetros de base de datos, JWT y correo en `Settings(BaseSettings)`, con carga de entorno. Esta convención de URL corresponde a la API propia: el mapa utiliza direcciones explícitas de OpenStreetMap.
- **Justificación:** permite cambiar el destino de la API y parámetros de ejecución sin modificar cada consumidor.

#### G4. Controles estáticos explícitos — herramientas configuradas

- **Descripción:** expresar mediante configuración controles repetibles sobre el código.
- **Implementación:** `npm run lint` ejecuta ESLint con reglas recomendadas de JavaScript, TypeScript, React Hooks y React Refresh. `npm run build` ejecuta `tsc -b` antes de Vite. TypeScript controla locales y parámetros no utilizados y caídas entre casos de `switch`. Ruff declara familias `E`, `F`, `I`, `N`, `W` y `UP`, destino Python 3.12 y longitud de línea 120, con `E501` y `N818` ignoradas.
- **Justificación:** permite detectar problemas repetibles de uso del lenguaje, imports y hooks antes de distribuir la aplicación.

### 2.2. Frontend

#### F1. Componentes funcionales con contratos de props — recurrente

- **Descripción:** expresar la interfaz mediante funciones React y entradas tipadas.
- **Implementación:** las páginas se exportan como funciones y los componentes con parámetros declaran interfaces de props. `ShipmentMapProps` tipa coordenadas, modo y callback; `ProtectedRoutesProps` tipa los roles admitidos.
- **Justificación:** hace explícito qué información necesita cada componente y facilita su reutilización.

#### F2. Acceso HTTP en servicios y coordinación mediante hooks — recurrente

- **Descripción:** separar las solicitudes de red de la representación visual.
- **Implementación:** `CreateUserPage` invoca `useCreateUser`, que configura una mutación y delega a `createUser`; el servicio construye headers y cuerpo. Seguimiento repite el recorrido página → hook → servicio. Las páginas conservan lógica de formulario y presentación; no se afirma que toda su lógica haya sido extraída.
- **Justificación:** permite ajustar el contrato HTTP sin trasladar ese cambio a la estructura visual y reutilizar operaciones.

#### F3. Separación de estado local, sesión global y datos remotos — recurrente

- **Descripción:** asignar cada estado al mecanismo que lo administra en el proyecto.
- **Implementación:** `useState` mantiene formularios; Redux registra únicamente el reducer `auth`; TanStack Query administra consultas y mutaciones. `RootState`, `AppDispatch`, `useAppSelector` y `useAppDispatch` vinculan el acceso al store con sus tipos. Un listener middleware persiste los cambios de sesión fuera de los reducers.
- **Justificación:** evita mantener copias globales de respuestas remotas y separa efectos de persistencia de las actualizaciones del estado.

#### F4. Caché identificada por parámetros y actualización explícita — recurrente; políticas por operación

- **Descripción:** identificar qué recurso representa cada consulta y actualizarlo cuando una operación lo modifica.
- **Implementación:** seguimiento utiliza `['tracking', token]` y se habilita cuando existe token; sucursales utiliza `['branches']`. El registro de retiro invalida `['pickup-validation']` y `['tracking']`. Seguimiento no reintenta un 404 y define treinta segundos de vigencia; sucursales define diez minutos. Son decisiones por operación, no una política temporal uniforme.
- **Justificación:** evita compartir datos entre códigos diferentes y reduce la presentación de resultados anteriores a una mutación.

#### F5. Contratos de transporte diferenciados de modelos internos — recurrente

- **Descripción:** delimitar las estructuras de la API y los nombres utilizados en la interfaz.
- **Implementación:** los contratos `ApiUser` y `ApiCreatedUser` conservan los nombres recibidos; los mapeos producen `AuthUser` y `CreatedUser`. Por ejemplo, `requiere_cambio_password` se convierte en `requiresPasswordChange` y `password_temporal` en `temporaryPassword`. Al enviar empleados, `roleId` se transforma en `rol_id`.
- **Justificación:** concentra la adaptación al contrato backend y mantiene camelCase en los modelos de interfaz.

#### F6. Tratamiento de fallas HTTP y estados visibles — recurrente

- **Descripción:** convertir fallas remotas en errores que la interfaz pueda presentar.
- **Implementación:** los servicios distinguen fallas de conexión, respuestas HTTP no exitosas, JSON ilegible y estructuras inesperadas. Las clases `AuthApiError`, `UsersApiError` y `TrackingApiError` representan errores por dominio. Los formularios y consultas consumen estados como `isPending`, `isFetching` e `isError` para deshabilitar acciones, mostrar carga y ofrecer reintentos.
- **Justificación:** evita interpretar una respuesta fallida como datos válidos y permite explicar el resultado al usuario.

#### F7. Rutas centralizadas y protección de acceso — recurrente

- **Descripción:** separar declaraciones públicas y privadas y aplicar controles de acceso en un punto común.
- **Implementación:** `AppRouter` compone `authRoutes` y coloca `mainRoutes` bajo `ProtectedRoutes`. Este último comprueba autenticación y, cuando corresponde, roles. `AuthBootstrap` valida la sesión persistida con el backend antes de mostrar el área privada. `navigation.ts` comparte el catálogo de accesos entre Home y layout; los roles de las rutas privadas también se declaran en `MainRoutes`.
- **Justificación:** mantiene un límite de acceso visible en el router y evita considerar suficiente la presencia de un token almacenado.

#### F8. Tokens visuales, estilos reutilizados y accesibilidad explícita — recurrente

- **Descripción:** compartir decisiones visuales y aportar semántica a controles y mensajes.
- **Implementación:** `theme.css` define variables y tema oscuro; `forms.css` reutiliza clases de campos, controles y errores. Se observan clases con bloque, elemento y modificador, por ejemplo `tracking-feedback--error`. Las páginas usan `lucide-react`, asociaciones `label`/`id`, `aria-label`, `role="alert"` y regiones `aria-live`. Hay foco visible global y media queries para adaptar vistas; el tema establece 320 px como ancho mínimo.
- **Justificación:** conserva coherencia visual y facilita reconocer controles, foco y cambios de estado.

#### F9. Gestión del ciclo de vida de recursos externos — decisión específica

- **Descripción:** inicializar y liberar recursos imperativos integrados con React.
- **Implementación:** `ShipmentMap` mantiene mapa y marcador en refs, crea Leaflet dentro de un efecto y ejecuta `map.remove()` en su limpieza. Otros efectos actualizan callback y coordenadas con sus dependencias declaradas.
- **Justificación:** evita conservar mapas y manejadores después del desmontaje o de una recreación del recurso.

### 2.3. Backend

#### B1. Routers que delegan casos de uso a servicios — recurrente

- **Descripción:** conservar el adaptador HTTP separado de las decisiones principales de negocio.
- **Implementación:** los routers declaran rutas, contratos, códigos de estado y dependencias. El alta de empleados delega directamente en `ServicioEmpleados`; el registro de envíos llama a `ServicioEnvios` y programa notificaciones mediante `BackgroundTasks`.
- **Justificación:** permite comprender el contrato HTTP sin mezclarlo con validación de unicidad, creación de modelos o generación de códigos.

#### B2. Interfaces y composición mediante inyección de dependencias — recurrente, con aislamiento parcial

- **Descripción:** declarar operaciones esperadas y entregar colaboradores al consumidor.
- **Implementación:** protocolos como `IRepositorioUsuarios` especifican métodos asíncronos. Los constructores de servicios reciben repositorios y las funciones `get_*` en `dependencies.py` conectan implementaciones usando `Depends`. Los tests sustituyen dependencias de sesión y fábrica de sesiones.
- **Justificación:** hace visibles los colaboradores y permite reemplazar persistencia en pruebas sin cambiar los endpoints.

#### B3. DTO Pydantic separados del ORM y validación en la entrada — recurrente

- **Descripción:** representar solicitudes y respuestas con contratos distintos de los modelos de persistencia.
- **Implementación:** los contratos heredan de `ApiModel`; usan `Field`, `EmailStr`, `field_validator` y `model_validator`. `CrearEmpleadoRequest` comprueba DNI y teléfono; `CrearEnvioRequest` exige paquetes y valida destino según tipo de entrega. Los routers declaran `response_model` y los servicios construyen respuestas explícitas.
- **Justificación:** rechaza entradas incompatibles y controla qué información integra la respuesta pública.

#### B4. Reglas de negocio puras y constantes compartidas — recurrente

- **Descripción:** aislar cálculos y restricciones que no requieren HTTP ni persistencia.
- **Implementación:** `validar_paquete` devuelve errores por campo para peso y dimensiones; módulos separados resuelven contraseñas, códigos, destinos, recepción y retiro. Los límites de paquetes son constantes con nombre. Roles, alcances y estados se agrupan en `domain/constants`.
- **Justificación:** facilita reutilizar decisiones y comprobar valores límite sin iniciar la API o una base de datos.

#### B5. Persistencia encapsulada y acceso asíncrono — recurrente

- **Descripción:** concentrar consultas y escrituras en repositorios con sesiones asíncronas.
- **Implementación:** los repositorios usan expresiones `select` y `update` de SQLAlchemy y esperan operaciones con `await`. La sesión se obtiene con un generador de dependencia, que realiza rollback ante una excepción y cierra el recurso. Los repositorios efectúan los commits; usuarios y envíos cargan relaciones con `selectinload` o `joinedload`.
- **Justificación:** evita dispersar consultas en routers, delimita la vida de la sesión y prepara las relaciones necesarias sin depender de cargas implícitas posteriores.

#### B6. Integridad de datos y esquema versionado — recurrente en persistencia

- **Descripción:** representar restricciones de datos en modelos y registrar cambios de esquema.
- **Implementación:** los modelos declaran claves foráneas, nulabilidad, campos únicos y restricciones de comprobación. DNI, email, token de seguimiento y número de paquete tienen unicidad declarada. Alembic contiene configuración y una revisión inicial del esquema. Los servicios también consultan duplicados antes de crear usuarios o códigos.
- **Justificación:** complementa la validación de aplicación con restricciones de persistencia y conserva un historial explícito del esquema.

#### B7. Excepciones funcionales y traducción HTTP centralizada — recurrente

- **Descripción:** comunicar fallas esperadas con excepciones de aplicación y serializarlas en un punto común.
- **Implementación:** `AppException` contiene código, mensaje, estado HTTP y errores opcionales. Las especializaciones expresan validación, duplicados, autenticación y permisos. Los manejadores globales devuelven `status`, `code`, `message` y, cuando corresponde, `errors`. La validación de solicitudes se transforma a HTTP 400. Las excepciones inesperadas se registran con traceback y producen un mensaje genérico de HTTP 500.
- **Justificación:** mantiene un formato reconocible para consumidores y evita devolver el traceback de errores inesperados.

#### B8. Hashing de contraseñas y autorización en el servidor — recurrente

- **Descripción:** separar la verificación de credenciales de la autorización de operaciones.
- **Implementación:** `HasherContrasenas` genera y verifica hashes bcrypt; el alta persiste `password_hash` y devuelve la clave temporal en su respuesta inicial. `ManejadorJWT` emite tokens firmados con expiración y alcance. Las dependencias de rol consultan al usuario, comprueban estado activo y rol, y rechazan tokens restringidos al cambio de contraseña antes de permitir operaciones protegidas.
- **Justificación:** evita persistir contraseñas en claro y mantiene el control de acceso aunque se invoque la API directamente.

#### B9. Pruebas separadas por nivel y aisladas de la base de desarrollo — recurrente

- **Descripción:** comprobar reglas, integración HTTP y algunas dependencias arquitectónicas con alcances diferenciados.
- **Implementación:** `tests/unit` verifica reglas y utilidades; `tests/integration` utiliza HTTPX con transporte ASGI y fixtures de SQLite en memoria; `tests/architecture` analiza imports con AST. La fixture crea y elimina tablas por prueba y reemplaza dependencias de base de datos.
- **Justificación:** permite probar límites y permisos de manera repetible, sin depender de datos persistentes del entorno de desarrollo.

### 2.4. Decisiones específicas adicionales

Estas decisiones tienen evidencia concreta y aportan calidad dentro de su funcionalidad, pero no se elevan a convenciones generales:

| Criterio y descripción | Implementación | Justificación |
|---|---|---|
| Códigos públicos aleatorios: evitar identificadores secuenciales de seguimiento. | `secrets.choice` genera sufijos; el servicio consulta existencia y limita a cinco intentos la generación de candidatos. | Dificulta la enumeración secuencial y acota reintentos; no elimina por sí solo toda posibilidad de adivinación o carrera.
| Respuesta de seguimiento seleccionada: construir un DTO específico de consulta. | El servicio devuelve destino, coordenadas y datos de paquetes; no serializa el envío ORM completo ni incluye campos de contacto del remitente o destinatario. | Limita los campos publicados respecto del modelo persistido. El destino puede contener una dirección y los paquetes incluyen descripción y observaciones: no se afirma anonimización completa.
| Notificaciones posteriores al registro: diferir el envío de correo. | El router usa `BackgroundTasks`; el servicio recibe una fábrica y abre una sesión propia para procesar notificaciones. | Separa el envío de correo del armado de la respuesta y del ciclo de sesión de la solicitud. No acredita una cola durable ni entrega garantizada.
| Correlación de solicitudes: identificar operaciones para diagnóstico. | La fábrica de FastAPI registra `CorrelationIdMiddleware` y configura logging al iniciar. El formato de logs examinado no incorpora explícitamente el identificador. | Aporta identificación de solicitudes; no demuestra correlación automática de todas las líneas de log.

## 3. Errores comunes y prácticas utilizadas para prevenirlos

Los errores siguientes representan riesgos propios de las tecnologías utilizadas; su inclusión no significa que todos hayan ocurrido. La prevención se relaciona exclusivamente con mecanismos identificados. Cada fila referencia criterios y evidencias desarrollados en la sección 3.

| Error habitual | Por qué representa un problema | Práctica existente y alcance preventivo |
|---|---|---|
| Dispersar nombres y responsabilidades sin una convención. | Dificulta localizar una operación y comprender el impacto de cambios. | G1 y G2: nombres por lenguaje y módulos por responsabilidad. |
| Construir solicitudes HTTP dentro de las vistas. | Acopla presentación, transporte y errores de red. | F2: páginas → hooks → servicios; ajustes de contrato quedan en los servicios. |
| Duplicar datos remotos en Redux y en otra caché. | Puede producir valores contradictorios y actualizaciones descoordinadas. | F3: Redux conserva sesión y TanStack Query administra respuestas remotas. |
| Usar la misma clave de caché para distintos códigos consultados. | Puede mostrar el recurso de otra consulta. | F4: `queryKey` incluye el token o código que identifica los datos. |
| Mantener datos anteriores después de registrar un retiro. | La interfaz puede seguir mostrando un paquete como pendiente. | F4: la mutación invalida las consultas de retiro y seguimiento. |
| Tratar todo `fetch` resuelto como éxito o asumir JSON válido. | Una respuesta HTTP fallida o ilegible puede llegar al render como datos útiles. | F6: comprobación de `response.ok`, lectura tolerante de JSON y comprobaciones básicas de estructura. |
| Confundir interfaces TypeScript con validación completa del servidor. | Los datos de ejecución pueden no corresponder al tipo declarado. | F5: contratos y mapeos explícitos, con comprobaciones parciales de forma. La cobertura no es exhaustiva. |
| Mezclar nombres de API con modelos de UI. | Extiende detalles del contrato a páginas y formularios. | F5: adaptación explícita de snake_case a camelCase en servicios. |
| No mostrar carga, error o resultado de una operación. | El usuario pierde la referencia sobre lo que está ocurriendo y puede repetir acciones. | F6 y F8: estados de Query, controles deshabilitados y mensajes accesibles. |
| Confiar en un token almacenado u ocultar un botón como único control de acceso. | El usuario puede invocar una URL o la API directamente. | F7 y B8: validación de sesión, rutas protegidas y autorización backend. |
| Crear recursos de Leaflet sin liberarlos al desmontar. | Puede conservar instancias y manejadores que ya no corresponden a la vista. | F9: limpieza explícita del mapa en el efecto. Prevención específica de ese componente. |
| Concentrar SQL y reglas de negocio en endpoints. | Aumenta acoplamiento y dificulta probar la lógica. | B1, B4 y B5: routers delegan, reglas puras validan y repositorios consultan. |
| Aceptar datos sólo porque el formulario los validó. | La API puede consumirse sin el frontend. | B3 y B4: contratos Pydantic y reglas backend vuelven a validar. |
| Acceder a relaciones ORM no preparadas en un flujo asíncrono. | Puede intentar una carga implícita fuera del contexto adecuado. | B5: carga explícita de roles y paquetes en los repositorios examinados. |
| Mantener una sesión fallida sin rollback o sin cierre. | Puede afectar operaciones posteriores y retener recursos. | B5: dependencia con rollback ante excepción y cierre; no revierte commits anteriores. |
| Suponer que una consulta previa garantiza unicidad concurrente. | Dos solicitudes pueden observar que un dato todavía no existe. | B6: restricciones únicas complementan consultas previas; no se acredita traducción funcional uniforme de todas las colisiones. |
| Devolver excepciones internas directamente al consumidor. | Expone información técnica y genera contratos inconsistentes. | B7: errores funcionales estructurados y mensaje genérico para excepciones inesperadas. |
| Persistir contraseñas en texto claro o usar un token temporal para operar. | Expone credenciales y permite omitir el cambio obligatorio. | B8: hash bcrypt y rechazo del alcance temporal en dependencias de autorización. |
| Probar reglas sólo con casos válidos o contra una base con datos previos. | Omite valores límite y vuelve dependientes las pruebas del entorno. | B9: tests de límites y errores, fixtures y base en memoria por prueba. |

### Límites que no deben presentarse como prevención consolidada

Para conservar fidelidad al código, no se atribuyen al proyecto las siguientes garantías: separación estricta entre aplicación e infraestructura; validación exhaustiva del JSON frontend; TypeScript en modo estricto; ausencia total de secretos predeterminados en código; CORS restringido por origen; protección del token mediante cookies HttpOnly; ni revocación de JWT al cerrar sesión. Las evidencias son las importaciones y configuraciones señaladas en 2.2, G3, G4, F5 y B9, además de [CORS en main.py](../Back/app/api/main.py) y [persistencia de sesión en authStorage.ts](../front/src/features/auth/services/authStorage.ts).

Esta delimitación evita convertir herramientas disponibles o decisiones previstas en prácticas supuestamente verificadas; no constituye una propuesta de rediseño.

## 4. Lista de verificación

Aplicar a cada desarrollo o revisión. Marcar una sola respuesta por fila: **Sí / No / No aplica (N/A)**. «Sí» requiere una evidencia comprobable; «No aplica» corresponde a cambios que no afectan ese aspecto. Los identificadores remiten al criterio que fundamenta cada control. Las casillas quedan vacías para su uso posterior.

### 4.1. Criterios generales

| ID | Pregunta verificable | Sí | No | N/A |
|---|---|:---:|:---:|:---:|
| G1 | ¿Los componentes, hooks, clases, funciones y constantes respetan las convenciones de nombres del lenguaje y módulo donde se incorporan? | ☐ | ☐ | ☐ |
| G2 | ¿Los archivos nuevos están ubicados en la feature o capa correspondiente a su responsabilidad? | ☐ | ☐ | ☐ |
| G3 | ¿Las llamadas a la API propia construyen su URL desde `VITE_API_URL` y los parámetros backend se obtienen de `Settings` cuando corresponde? | ☐ | ☐ | ☐ |
| G4 | ¿Se ejecutaron `npm run lint` y `npm run build`, y se registró su resultado para la entrega? | ☐ | ☐ | ☐ |

### 4.2. Frontend

| ID | Pregunta verificable | Sí | No | N/A |
|---|---|:---:|:---:|:---:|
| F1 | ¿Las entradas de componentes y los modelos que intercambian tienen tipos explícitos acordes con los existentes? | ☐ | ☐ | ☐ |
| F2 | ¿Las llamadas HTTP permanecen en servicios y su coordinación remota utiliza hooks de la feature? | ☐ | ☐ | ☐ |
| F3 | ¿El estado de formulario permanece local y los datos remotos se administran con TanStack Query sin duplicarlos en Redux? | ☐ | ☐ | ☐ |
| F4 | ¿Las claves de consultas incluyen los parámetros que distinguen recursos y se invalidan las consultas afectadas por la mutación? | ☐ | ☐ | ☐ |
| F5 | ¿Los nombres snake_case del contrato se adaptan a los modelos internos camelCase en la frontera HTTP? | ☐ | ☐ | ☐ |
| F6 | ¿La operación contempla estado de carga, error y resultado, y deshabilita su envío mientras se procesa cuando corresponde? | ☐ | ☐ | ☐ |
| F7 | ¿Las rutas privadas quedan bajo `ProtectedRoutes` y sus roles concuerdan con los accesos que presenta la navegación? | ☐ | ☐ | ☐ |
| F8 | ¿Los estilos reutilizan tokens y clases comunes, y las acciones con iconos emplean `lucide-react`? | ☐ | ☐ | ☐ |
| F8 | ¿Los controles tienen labels o nombres accesibles, el foco es visible y los mensajes de error se anuncian mediante la semántica existente? | ☐ | ☐ | ☐ |
| F8 | ¿La vista conserva controles y contenido utilizables a 320 px y en los puntos de adaptación de su CSS? | ☐ | ☐ | ☐ |
| F9 | ¿Las integraciones que crean recursos imperativos, como el mapa, mantienen su actualización y limpieza al terminar el efecto? | ☐ | ☐ | ☐ |

### 4.3. Backend

| ID | Pregunta verificable | Sí | No | N/A |
|---|---|:---:|:---:|:---:|
| B1 | ¿El router declara el contrato HTTP y delega el caso de uso al servicio correspondiente? | ☐ | ☐ | ☐ |
| B2 | ¿Los repositorios consumidos por servicios tienen su interfaz correspondiente y se conectan mediante las dependencias existentes? | ☐ | ☐ | ☐ |
| B3 | ¿Las entradas y salidas usan contratos Pydantic, con validaciones y `response_model` acordes con la operación? | ☐ | ☐ | ☐ |
| B4 | ¿Las reglas puras existentes se reutilizan para validar el negocio y sus límites continúan expresados mediante constantes? | ☐ | ☐ | ☐ |
| B5 | ¿El acceso a datos queda en repositorios, espera las operaciones asíncronas y utiliza la gestión de sesión existente? | ☐ | ☐ | ☐ |
| B5 | ¿Las relaciones ORM utilizadas para construir respuestas se cargan explícitamente cuando lo requiere el flujo? | ☐ | ☐ | ☐ |
| B6 | ¿Los cambios del modelo conservan las restricciones de integridad aplicables y cuentan con su revisión de Alembic cuando alteran el esquema? | ☐ | ☐ | ☐ |
| B9 | ¿Las reglas o flujos modificados tienen pruebas de casos válidos y errores o límites relevantes dentro del nivel correspondiente? | ☐ | ☐ | ☐ |
| B9 | ¿Las pruebas de integración utilizan las fixtures y dependencias de base de datos de prueba? | ☐ | ☐ | ☐ |
| B9 | ¿Se ejecutaron `pip check` y `pytest -q` con `.venv/Scripts/python.exe` desde `Back/` cuando hubo cambios backend? | ☐ | ☐ | ☐ |

### 4.4. Seguridad y manejo de errores

| ID | Pregunta verificable | Sí | No | N/A |
|---|---|:---:|:---:|:---:|
| F6 | ¿El servicio HTTP maneja fallas de red, estado HTTP fallido y respuesta ilegible o inesperada antes de devolver datos a la UI? | ☐ | ☐ | ☐ |
| B7 | ¿Los errores funcionales utilizan las excepciones existentes y conservan el formato común sin devolver tracebacks al cliente? | ☐ | ☐ | ☐ |
| B8 | ¿Las contraseñas que se guardan pasan por el hasher y se conserva el cambio obligatorio de la contraseña temporal? | ☐ | ☐ | ☐ |
| B8 | ¿Las operaciones privadas aplican las dependencias backend de autenticación y rol correspondientes, incluido el rechazo del token temporal? | ☐ | ☐ | ☐ |
| B3 | ¿La respuesta pública contiene sólo los campos definidos por el DTO específico de esa operación? | ☐ | ☐ | ☐ |

## 5. Conclusión

El proyecto presenta convenciones recurrentes de nomenclatura, modularidad, separación de responsabilidades y contratos explícitos. En frontend, la organización por features, la división entre hooks y servicios y la asignación diferenciada del estado contribuyen a la consistencia del código. Los tokens visuales y los mecanismos accesibles observados sostienen una interfaz compartida entre funcionalidades.

En backend, los routers que delegan en servicios, los contratos Pydantic, las reglas de dominio comprobables de forma independiente, los repositorios asíncronos y las excepciones normalizadas facilitan comprender y verificar el comportamiento. Las pruebas unitarias, de integración y de arquitectura aportan controles complementarios, con los alcances descritos.

Estos criterios constituyen una base verificable para mantener la calidad y la legibilidad. Su formalización conserva los límites reales de la implementación: una interfaz declarada, un contrato de imports configurado o una herramienta disponible no acreditan por sí solos cumplimiento general. La checklist permite revisar futuros cambios a partir de prácticas efectivamente observadas, sin atribuir al sistema garantías que el código no respalda.
