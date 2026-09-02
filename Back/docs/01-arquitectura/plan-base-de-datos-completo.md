# Plan completo de base de datos (HU01–HU13)

Este documento diseña el modelo de datos para **todo** el Product Backlog (HU01 a HU13), no solo lo ya implementado. El objetivo es poder crear el esquema completo una sola vez en PostgreSQL (Neon) y que cada sprint futuro solo tenga que construir la lógica de aplicación sobre tablas que ya existen, en vez de ir migrando la base a los saltos.

Se apoya en dos fuentes: el Product Backlog completo (HU01–HU13, con sus escenarios BDD) y lo que ya está implementado y probado en `Back/app/infrastructure/db/models.py` (ver [Modelo de datos](./modelo-de-datos.md), que documenta el estado *actual*; este documento describe el estado *objetivo*).

**Estado: ya aplicado.** Las 15 tablas están definidas en `models.py`, cubiertas por la migración `app/infrastructure/db/migrations/versions/5c87e509d4e7_esquema_inicial_completo_hu01_hu13.py`, y probadas (`alembic upgrade head` / `downgrade base` de punta a punta, `pytest` completo). Ver la sección 8 para aplicarla contra Neon.

---

## 1. Criterio de diseño

- **Una sola base, un solo esquema `public`.** No hace falta separar lectura/escritura ni multi-tenant para este proyecto.
- **Nombres de tabla y columna en español**, `snake_case`, igual que el código ya existente (`domain_rules`, `envios`, `paquetes`, etc.).
- **Claves primarias:**
  - `UUID` para entidades que crea un usuario final y que viajan por la API pública (usuarios, envíos, paquetes, reclamos, recorridos, eventos de entrega) — evita exponer IDs secuenciales adivinables en un endpoint público como `/seguimiento`.
  - `SERIAL`/`BIGSERIAL` (entero autoincremental) para catálogos fijos (`roles`, `sucursales`) y para tablas de auditoría/log de alto volumen (`historial_estados_paquete`) donde no hace falta un UUID y un entero es más liviano de indexar.
- **Generación de UUID en la aplicación** (`uuid.uuid4()`, como ya hace SQLAlchemy en `models.py`), no en PostgreSQL. Esto evita depender de la extensión `pgcrypto`/`uuid-ossp` en Neon — una menos cosa que configurar en el servidor.
- **Timestamps:** `TIMESTAMPTZ` (con zona horaria) en todo, `created_at` con default `now()`, `updated_at` con default + `onupdate` donde la fila se edita.
- **Estados como texto validado en la aplicación** (`VARCHAR` + `CHECK`), no `ENUM` nativo de Postgres — un `ENUM` de Postgres requiere `ALTER TYPE` para agregar un valor nuevo, lo cual es más fricción que cambiar una constante en Python. Ya es el patrón que usa el código actual (`estado: Mapped[str]`).
- **Ninguna tabla nueva reemplaza lo ya construido para HU01–HU04.** Se listan igual, completas, para que este documento sea el mapa único de toda la base.

---

## 2. Diagrama completo

```mermaid
erDiagram
    ROLES ||--o{ USUARIOS : "tiene"
    USUARIOS ||--o| REPARTIDORES : "es (si rol=REPARTIDOR)"
    SUCURSALES ||--o{ REPARTIDORES : "base de"
    SUCURSALES ||--o{ ENVIOS : "recibe (si sucursal)"
    SUCURSALES ||--o{ RECORRIDOS : "origen de"
    SUCURSALES ||--o{ PAQUETES : "ubicacion actual"
    ENVIOS ||--|{ PAQUETES : "contiene"
    ENVIOS ||--o{ NOTIFICACIONES_ENVIO : "notifica"
    ENVIOS ||--o{ RECLAMOS : "puede reclamarse"
    PAQUETES ||--o{ HISTORIAL_ESTADOS_PAQUETE : "registra cambios"
    PAQUETES ||--o{ RECLAMOS : "puede reclamarse"
    PAQUETES ||--o| RECORRIDO_PAQUETES : "asignado a"
    RECORRIDOS ||--|{ RECORRIDO_PAQUETES : "incluye"
    RECORRIDOS ||--o{ ALERTAS_RECORRIDO : "genera"
    REPARTIDORES ||--o{ RECORRIDOS : "realiza"
    REPARTIDORES ||--o| POSICION_ACTUAL_REPARTIDOR : "ubicacion actual"
    PAQUETES ||--o{ EVENTOS_ENTREGA : "registra"
    USUARIOS ||--o{ EVENTOS_ENTREGA : "registra (repartidor/sucursal)"
    USUARIOS ||--o{ HISTORIAL_ESTADOS_PAQUETE : "provoca cambio"

    ROLES {
        int id PK
        string nombre
    }
    USUARIOS {
        uuid id PK
        string dni UK
        string email UK
        int rol_id FK
        string estado
        bool requiere_cambio_password
    }
    REPARTIDORES {
        uuid usuario_id PK_FK
        int sucursal_base_id FK
        string tipo_reparto "CORTA | LARGA"
        bool activo
    }
    SUCURSALES {
        int id PK
        string nombre
        float latitud
        float longitud
    }
    ENVIOS {
        uuid id PK
        string token_seguimiento UK
        string tipo_entrega
        int sucursal_destino_id FK
        float latitud_destino
        float longitud_destino
    }
    PAQUETES {
        uuid id PK
        uuid envio_id FK
        string numero_paquete UK
        string estado
        int sucursal_actual_id FK
    }
    HISTORIAL_ESTADOS_PAQUETE {
        bigint id PK
        uuid paquete_id FK
        string estado_anterior
        string estado_nuevo
        uuid usuario_id FK
        int sucursal_id FK
        timestamptz created_at
    }
    NOTIFICACIONES_ENVIO {
        uuid id PK
        uuid envio_id FK
        string canal "EMAIL | WHATSAPP"
        string destinatario_tipo
        string estado
    }
    RECLAMOS {
        uuid id PK
        uuid envio_id FK
        uuid paquete_id FK
        string tipo
        string estado
    }
    PREGUNTAS_FRECUENTES {
        int id PK
        string categoria
        string pregunta
        bool publicada
    }
    RECORRIDOS {
        uuid id PK
        uuid repartidor_id FK
        int sucursal_origen_id FK
        string tipo_distancia "CORTA | LARGA"
        date fecha
        string estado
    }
    RECORRIDO_PAQUETES {
        uuid id PK
        uuid recorrido_id FK
        uuid paquete_id FK
        int orden
        string estado_en_recorrido
    }
    ALERTAS_RECORRIDO {
        uuid id PK
        uuid paquete_id FK
        string motivo
        bool resuelta
    }
    POSICION_ACTUAL_REPARTIDOR {
        uuid repartidor_id PK_FK
        uuid recorrido_id FK
        float latitud
        float longitud
        timestamptz actualizado_at
    }
    EVENTOS_ENTREGA {
        uuid id PK
        uuid paquete_id FK
        string tipo_evento "ENTREGA_DOMICILIO | RETIRO_SUCURSAL"
        string resultado "EXITOSO | FALLIDO"
        uuid usuario_registro_id FK
        int sucursal_id FK
        timestamptz created_at
    }
```

15 tablas en total: 5 ya usadas por lógica de aplicación implementada (`roles`, `usuarios`, `sucursales`, `envios`, `paquetes`, HU01-HU04) y 10 nuevas creadas en el esquema para cuando se implemente cada HU (`repartidores`, `historial_estados_paquete`, `notificaciones_envio`, `reclamos`, `preguntas_frecuentes`, `recorridos`, `recorrido_paquetes`, `alertas_recorrido`, `posicion_actual_repartidor`, `eventos_entrega`).

---

## 3. Tablas por dominio

### 3.1 Identidad y accesos — HU01, HU02 (ya implementado)

`roles` y `usuarios`, sin cambios respecto a lo documentado en [Modelo de datos](./modelo-de-datos.md). No se propone ninguna modificación acá.

### 3.2 Repartidores — soporte de HU10, HU11, HU12 (nueva)

Extensión 1 a 1 de `usuarios` para no llenar la tabla de usuarios con columnas que solo aplican al rol `REPARTIDOR`.

```sql
CREATE TABLE repartidores (
    usuario_id      UUID PRIMARY KEY REFERENCES usuarios(id),
    sucursal_base_id INT NOT NULL REFERENCES sucursales(id),
    tipo_reparto    VARCHAR(10) NOT NULL CHECK (tipo_reparto IN ('CORTA', 'LARGA')),
    activo          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

- `tipo_reparto` decide si al repartidor se le asignan recorridos `CORTA` (misma ciudad, entrega a domicilio) o `LARGA` (entre ciudades, deja paquetes en sucursales) — HU10 Escenario 4.
- `sucursal_base_id` es la sucursal desde la que arranca sus recorridos.

### 3.3 Sucursales — HU03, HU09 (ya implementado)

Sin cambios.

### 3.4 Envíos y paquetes — HU03, HU04 (ya implementado + un agregado)

`envios`: sin cambios.

`paquetes`: se agrega **una** columna nueva:

```sql
ALTER TABLE paquetes ADD COLUMN sucursal_actual_id INT REFERENCES sucursales(id);
```

- Refleja dónde está físicamente el paquete en este momento (`NULL` hasta que HU06 lo escanea por primera vez). Es lo que permite armar el mensaje de HU04 Escenario 5 ("Ingresó a la sucursal de {ciudad}") sin tener que recorrer todo `historial_estados_paquete` para saber la ubicación actual.

### 3.5 Historial de estados del paquete — soporta HU04 (Esc. 5/6), HU06, HU10-HU13 (nueva)

Tabla de auditoría append-only: cada cambio de estado de un paquete queda registrado, quién lo hizo y desde dónde.

```sql
CREATE TABLE historial_estados_paquete (
    id              BIGSERIAL PRIMARY KEY,
    paquete_id      UUID NOT NULL REFERENCES paquetes(id),
    estado_anterior VARCHAR(30),
    estado_nuevo    VARCHAR(30) NOT NULL,
    usuario_id      UUID REFERENCES usuarios(id),
    sucursal_id     INT REFERENCES sucursales(id),
    latitud         DOUBLE PRECISION,
    longitud        DOUBLE PRECISION,
    observacion     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_historial_estados_paquete_id ON historial_estados_paquete(paquete_id, created_at);
```

- `usuario_id` es `NULL` cuando el cambio lo genera el sistema (por ejemplo, un evento automático de proximidad de HU11 Escenario 3), y tiene valor cuando lo genera una persona (vendedor que escanea, repartidor que marca entrega).
- Cada vez que se inserta una fila acá, la aplicación también actualiza `paquetes.estado` (y `paquetes.sucursal_actual_id` si corresponde) para que la consulta pública de HU04 siga siendo una lectura simple sin JOIN — este historial es para trazabilidad interna y reportes, no reemplaza el campo denormalizado.

**Máquina de estados propuesta** (los nombres son constantes de dominio, ver sección 4):

```mermaid
stateDiagram-v2
    [*] --> PENDIENTE: HU03 registro
    PENDIENTE --> EN_SUCURSAL_ORIGEN: HU06 escaneo en terminal
    EN_SUCURSAL_ORIGEN --> EN_TRANSITO: HU10 recorrido larga distancia asignado
    EN_SUCURSAL_ORIGEN --> EN_REPARTO: HU10 recorrido corta distancia asignado
    EN_TRANSITO --> EN_SUCURSAL_DESTINO: HU11 proximidad 10km (Esc. 3)
    EN_SUCURSAL_DESTINO --> EN_REPARTO: HU10 recorrido corta distancia (ciudad destino)
    EN_SUCURSAL_DESTINO --> RETIRADO: HU13 retiro en sucursal
    EN_REPARTO --> ENTREGADO: HU12 entrega exitosa
    EN_REPARTO --> ENTREGA_FALLIDA: HU12 intento fallido
    ENTREGA_FALLIDA --> EN_REPARTO: reintento (nuevo recorrido)
    ENTREGADO --> [*]
    RETIRADO --> [*]
```

Hoy (HU03/HU04 ya implementadas) un paquete solo llega a `PENDIENTE` — el resto de los estados están definidos acá para que cuando se implemente cada HU no haya que rediseñar el campo `estado` ni renegociar nombres con el frontend a mitad de camino.

### 3.6 Notificaciones — HU05 (nueva)

```sql
CREATE TABLE notificaciones_envio (
    id                  UUID PRIMARY KEY,
    envio_id            UUID NOT NULL REFERENCES envios(id),
    canal               VARCHAR(10) NOT NULL CHECK (canal IN ('EMAIL', 'WHATSAPP')),
    destinatario_tipo   VARCHAR(15) NOT NULL CHECK (destinatario_tipo IN ('REMITENTE', 'DESTINATARIO')),
    destino             VARCHAR(150) NOT NULL,
    estado              VARCHAR(15) NOT NULL DEFAULT 'PENDIENTE' CHECK (estado IN ('PENDIENTE', 'ENVIADO', 'FALLIDO')),
    proveedor_mensaje_id VARCHAR(150),
    error_detalle       TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_notificaciones_envio_envio ON notificaciones_envio(envio_id);
```

- Un envío exitoso de HU03 genera hasta 4 filas acá (email+WhatsApp × remitente+destinatario). Permite reintentar solo el canal que falló sin reenviar todo, y auditar si el token realmente llegó.
- `proveedor_mensaje_id` guarda el ID que devuelva el proveedor externo (ej. Twilio para WhatsApp, SendGrid/SES para email) — útil para debug sin acoplar el esquema a un proveedor específico.

### 3.7 Reclamos — HU07 (nueva)

```sql
CREATE TABLE reclamos (
    id                  UUID PRIMARY KEY,
    envio_id            UUID NOT NULL REFERENCES envios(id),
    paquete_id          UUID REFERENCES paquetes(id),
    tipo                VARCHAR(20) NOT NULL CHECK (tipo IN ('DEMORA', 'DANIO', 'EXTRAVIO', 'OTRO')),
    descripcion         TEXT NOT NULL,
    contacto_nombre     VARCHAR(150) NOT NULL,
    contacto_email      VARCHAR(150),
    contacto_telefono   VARCHAR(30),
    estado              VARCHAR(15) NOT NULL DEFAULT 'ABIERTO' CHECK (estado IN ('ABIERTO', 'EN_REVISION', 'RESUELTO', 'RECHAZADO')),
    resolucion          TEXT,
    usuario_resolucion_id UUID REFERENCES usuarios(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_reclamos_envio ON reclamos(envio_id);
```

- `paquete_id` es opcional: el reclamo se inicia desde la vista de un envío (HU07 Escenario 1), pero puede referirse a un paquete puntual si el envío tiene varios.
- Es un endpoint público (como HU03/HU04), por eso los datos de contacto se cargan en el reclamo mismo en vez de exigir sesión.

### 3.8 Preguntas frecuentes — HU08 (nueva)

```sql
CREATE TABLE preguntas_frecuentes (
    id          SERIAL PRIMARY KEY,
    categoria   VARCHAR(80),
    pregunta    VARCHAR(255) NOT NULL,
    respuesta   TEXT NOT NULL,
    orden       INT NOT NULL DEFAULT 0,
    publicada   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Nota abierta:** esta es la única tabla del plan que podría no hacer falta — si el contenido de preguntas frecuentes es fijo y lo mantiene el equipo de frontend directamente en el código, no se necesita tabla ni endpoint. Se incluye como opción si en cambio se quiere que alguien pueda editarlo sin desplegar. Ver pregunta abierta en la sección 6.

### 3.9 Recorridos — HU10 (nueva)

```sql
CREATE TABLE recorridos (
    id                      UUID PRIMARY KEY,
    repartidor_id           UUID NOT NULL REFERENCES repartidores(usuario_id),
    sucursal_origen_id      INT NOT NULL REFERENCES sucursales(id),
    tipo_distancia          VARCHAR(10) NOT NULL CHECK (tipo_distancia IN ('CORTA', 'LARGA')),
    fecha                   DATE NOT NULL,
    estado                  VARCHAR(15) NOT NULL DEFAULT 'GENERADO' CHECK (estado IN ('GENERADO', 'EN_EDICION', 'EN_CURSO', 'FINALIZADO')),
    generado_automaticamente BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE recorrido_paquetes (
    id                  UUID PRIMARY KEY,
    recorrido_id        UUID NOT NULL REFERENCES recorridos(id),
    paquete_id          UUID NOT NULL REFERENCES paquetes(id),
    orden               INT NOT NULL,
    estado_en_recorrido VARCHAR(15) NOT NULL DEFAULT 'PENDIENTE' CHECK (estado_en_recorrido IN ('PENDIENTE', 'ENTREGADO', 'FALLIDO')),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (recorrido_id, paquete_id),
    UNIQUE (recorrido_id, orden)
);

CREATE TABLE alertas_recorrido (
    id          UUID PRIMARY KEY,
    paquete_id  UUID NOT NULL REFERENCES paquetes(id),
    motivo      VARCHAR(40) NOT NULL DEFAULT 'SIN_RECORRIDO_ASIGNADO',
    resuelta    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    resuelta_at TIMESTAMPTZ
);
```

- No hay una tabla separada de "paradas": cada fila de `recorrido_paquetes` ya es la posición de un paquete en la ruta (`orden`). Para mostrar el mapa de un recorrido alcanza con leer `recorrido_paquetes` y hacer join contra el `envio`/`sucursal` de cada paquete para obtener las coordenadas.
- Un paquete no puede estar en dos recorridos al mismo tiempo — se garantiza a nivel de aplicación (buscar si ya tiene una fila en `recorrido_paquetes` con `estado_en_recorrido = 'PENDIENTE'` en otro recorrido activo antes de asignarlo). No se modela como constraint SQL porque involucra el estado del recorrido padre, no solo del paquete.
- `alertas_recorrido` implementa directamente HU10 Escenario 3: un job (o el mismo proceso de generación automática) inserta una fila acá por cada paquete que quedó sin asignar a ningún `recorrido_paquetes` al finalizar la generación/edición del día.

### 3.10 Ubicación del repartidor — HU11 (nueva)

```sql
CREATE TABLE posicion_actual_repartidor (
    repartidor_id   UUID PRIMARY KEY REFERENCES repartidores(usuario_id),
    recorrido_id    UUID REFERENCES recorridos(id),
    latitud         DOUBLE PRECISION NOT NULL,
    longitud        DOUBLE PRECISION NOT NULL,
    actualizado_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Decisión de diseño importante:** esto guarda solo la **última** posición conocida de cada repartidor (`UPSERT` en cada ping de ubicación), no un historial de todos los pings. Ninguna HU pide "ver el recorrido pasado del repartidor", solo su ubicación actual en el mapa (HU11 Escenario 1/2) — guardar cada ping en una tabla de historial sería una tabla de altísimo volumen (un repartidor moviéndose genera un ping cada pocos segundos) sin ningún caso de uso que lo consuma. Si en el futuro se pide un historial de recorridos reales para reportes, se agrega una tabla `historial_posiciones_repartidor` aparte en ese momento — no hace falta anticiparla ahora.

La proximidad de 10km al destino (HU11 Escenario 3, dispara el cambio de estado a `EN_SUCURSAL_DESTINO`) se calcula en la aplicación comparando esta posición contra las coordenadas de la sucursal destino en cada ping, no en SQL.

### 3.11 Entregas y retiros — HU12, HU13 (nueva, unificada)

HU12 (entrega a domicilio) y HU13 (retiro en sucursal) son, en el fondo, el mismo evento de negocio — "el paquete deja de estar en la red de la empresa y pasa a manos del destinatario" — con datos ligeramente distintos. Se modelan en una sola tabla para no duplicar campos casi idénticos (nombre y documento de quien recibe, fecha, quién lo registra) en dos tablas separadas:

```sql
CREATE TABLE eventos_entrega (
    id                      UUID PRIMARY KEY,
    paquete_id              UUID NOT NULL REFERENCES paquetes(id),
    tipo_evento             VARCHAR(20) NOT NULL CHECK (tipo_evento IN ('ENTREGA_DOMICILIO', 'RETIRO_SUCURSAL')),
    resultado               VARCHAR(10) NOT NULL CHECK (resultado IN ('EXITOSO', 'FALLIDO')),
    receptor_nombre         VARCHAR(150),
    receptor_documento      VARCHAR(20),
    es_autorizado           BOOLEAN NOT NULL DEFAULT FALSE,
    documento_destinatario_verificado BOOLEAN NOT NULL DEFAULT FALSE,
    firma_imagen            BYTEA,
    firma_content_type      VARCHAR(50),
    motivo_fallo            VARCHAR(255),
    usuario_registro_id     UUID NOT NULL REFERENCES usuarios(id),
    sucursal_id             INT REFERENCES sucursales(id),
    latitud                 DOUBLE PRECISION,
    longitud                DOUBLE PRECISION,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_eventos_entrega_paquete ON eventos_entrega(paquete_id, created_at);
```

- **HU12** (repartidor, `tipo_evento = 'ENTREGA_DOMICILIO'`): `resultado = 'EXITOSO'` con `receptor_nombre`/`receptor_documento` (Escenario 1, mayor de 16 con firma); o `resultado = 'FALLIDO'` con `motivo_fallo` (Escenario 3, ej. "persona no encontrada" — el teléfono del destinatario para contactarlo del Escenario 2 ya está en `envios.destinatario_telefono`, no hace falta duplicarlo acá). `latitud`/`longitud` quedan del repartidor al momento de la entrega, útil para disputas.
- **HU13** (personal de sucursal, `tipo_evento = 'RETIRO_SUCURSAL'`): `resultado` siempre `'EXITOSO'` (si no se cumplen las condiciones, no se registra nada — el retiro simplemente no ocurre). `es_autorizado = TRUE` cuando retira una persona distinta al destinatario (Escenario 2), y en ese caso `documento_destinatario_verificado = TRUE` confirma que se validó la copia del documento del destinatario presentada junto con la Autorización de Retiro física. No se modela la "Autorización de Retiro" como una entidad separada porque es un documento físico que se verifica en el momento, no algo que el sistema emita o pre-registre — si en el futuro se digitaliza ese flujo (autorización generada desde la app, con su propio ciclo de vida), ahí sí ameritaría su propia tabla.
- Un paquete puede tener **varias filas** acá: cada intento fallido de HU12 Escenario 3 es una fila nueva, y el intento exitoso final (o el retiro) es la última.
- `firma_imagen` (`BYTEA`) guarda el archivo de la firma **directamente en la base**, no en un storage externo — decisión explícita del equipo: por ahora no se terceriza nada. `firma_content_type` (ej. `image/png`) permite servirla de vuelta con el `Content-Type` correcto. Si el volumen lo justifica más adelante, migrar a un storage externo (S3, Cloudinary, etc.) es un cambio de aplicación — se reemplazaría esta columna por una URL sin tocar el resto de la tabla.

---

## 4. Constantes de dominio

Ya creadas en `app/domain/constants/estados_logistica.py`, siguiendo el patrón existente (`RolEnum`, `ScopeEnum`, `ErrorCodes`): `EstadoPaqueteEnum`, `TipoDistanciaEnum`, `CanalNotificacionEnum`, `DestinatarioNotificacionEnum`, `EstadoNotificacionEnum`, `TipoReclamoEnum`, `EstadoReclamoEnum`, `EstadoRecorridoEnum`, `EstadoRecorridoPaqueteEnum`, `TipoEventoEntregaEnum`, `ResultadoEventoEntregaEnum`.

Cada `CheckConstraint` de `models.py` se arma a partir de estos enums (helper `_lista_sql()` en el propio archivo), en vez de repetir los strings sueltos en cada `CHECK` — un solo lugar define qué valores son válidos. Ningún servicio los usa todavía (las HU05-HU13 no están implementadas), pero ya están ahí para cuando corresponda, y para que el esquema de base de datos no invente valores que el código de dominio tenga que rehacer después.

---

## 5. Índices y rendimiento

Además de los índices ya señalados junto a cada tabla:

| Tabla | Índice | Por qué |
|---|---|---|
| `paquetes` | ya existe `numero_paquete` (unique) | búsqueda por escaneo (HU06) |
| `envios` | ya existe `token_seguimiento` (unique) | búsqueda pública (HU04) |
| `recorrido_paquetes` | `(paquete_id)` | saber rápido si un paquete ya está en algún recorrido |
| `eventos_entrega` | `(paquete_id, created_at)` | listar el historial de intentos de un paquete en orden |
| `historial_estados_paquete` | `(paquete_id, created_at)` | timeline de un paquete (igual razón) |

Ninguna de estas tablas necesita particionado ni índices especiales de PostgreSQL (GIN, BRIN, etc.) al volumen esperado de un proyecto académico — se deja mencionado para no over-engineerizar la primera versión.

---

## 6. Decisiones tomadas

1. **`preguntas_frecuentes` (HU08): tabla en base.** Nada hardcodeado en el frontend — el contenido se administra desde la base, tabla creada.
2. **Firmas de entrega (HU12):** se guardan en la propia base (`eventos_entrega.firma_imagen`, `BYTEA`), no en un storage externo. El proyecto no terceriza nada por el momento.
3. **Las 15 tablas se crean todas ahora**, no incrementalmente HU por HU — ver sección 8.
4. **Proveedor de email/WhatsApp (HU05):** sigue sin definir, pero no bloquea nada del esquema — `notificaciones_envio.canal`/`proveedor_mensaje_id` ya son agnósticos de proveedor. Se decide cuando se implemente esa historia.

---

## 7. Qué se implementó exactamente

- `app/domain/constants/estados_logistica.py`: los 11 enums de la sección 4.
- `app/infrastructure/db/models.py`: las 10 tablas nuevas (`RepartidorModel`, `HistorialEstadoPaqueteModel`, `NotificacionEnvioModel`, `ReclamoModel`, `PreguntaFrecuenteModel`, `RecorridoModel`, `RecorridoPaqueteModel`, `AlertaRecorridoModel`, `PosicionActualRepartidorModel`, `EventoEntregaModel`) más la columna `paquetes.sucursal_actual_id`.
- `app/infrastructure/db/migrations/versions/5c87e509d4e7_esquema_inicial_completo_hu01_hu13.py`: migración de Alembic que crea las 15 tablas con sus índices y `CHECK` constraints. Probada de punta a punta (`upgrade head` y `downgrade base` contra SQLite).
- `app/infrastructure/db/session.py`: rama nueva para Postgres que pasa `ssl=require` como `connect_args` (ver sección 8, punto 3 — `asyncpg` no entiende `sslmode` en la URL como sí lo hace `psycopg2`).
- `asyncpg` y `alembic` ya estaban en `requirements.txt` de antes, no hizo falta agregar nada.
- No se tocó ningún servicio, contrato ni router: las 10 tablas nuevas no tienen todavía lógica de aplicación (eso se construye HU por HU cuando corresponda), solo existen en el esquema.
- `pytest` completo (51 tests) sigue en verde después de estos cambios.

## 8. Aplicar esto en Neon

1. **Conseguir el connection string.** En el panel de Neon (`Connect` → pestaña `Connection string`), copiar el que corresponde a la rama `production`. Neon da dos variantes:
   - **Pooled** (el host suele tener `-pooler` en el nombre): para la app en funcionamiento normal.
   - **Direct/unpooled**: para correr la migración de Alembic (algunos poolers en modo `transaction` no soportan bien el `DDL` de una migración).
2. **Armar la URL para SQLAlchemy async:** tomar el connection string de Neon y:
   - Cambiar `postgresql://` por `postgresql+asyncpg://`.
   - **Sacar el `?sslmode=require` del final** — ya lo maneja el código (`session.py`), y `asyncpg` no acepta ese parámetro en la URL.

   Ejemplo, a partir de `postgresql://usuario:password@ep-xxxx-pooler.neon.tech/gestion-envios?sslmode=require`:
   ```
   DATABASE_URL=postgresql+asyncpg://usuario:password@ep-xxxx-pooler.neon.tech/gestion-envios
   ```
3. **Correr la migración una sola vez, contra el endpoint *directo*:**
   ```powershell
   $env:DATABASE_URL = "postgresql+asyncpg://usuario:password@ep-xxxx.neon.tech/gestion-envios"
   & .\.venv\Scripts\python.exe -m alembic upgrade head
   ```
   Esto crea las 15 tablas en Neon. Se puede correr desde cualquier máquina con `Back/.venv` y red hacia Neon — no hace falta que sea el mismo servidor que corre la API.
4. **Configurar `Back/.env`** con el `DATABASE_URL` definitivo (el *pooled*, sin `sslmode`) para que la API lo use al arrancar.
5. **Arrancar la app normalmente** (`python run.py`). El `ejecutar_siembra()` de siempre corre: como las tablas ya existen (las creó Alembic), `crear_tablas()` no hace nada (es un `create_all` con `checkfirst`, no falla ni duplica), y el seed de roles/sucursales/Superadmin se aplica igual que en SQLite — es el mismo código, sin cambios.
6. **A futuro:** cualquier cambio de esquema (agregar una columna, una tabla nueva) se hace con `alembic revision --autogenerate -m "..."` + revisión manual + `alembic upgrade head` contra Neon — no volver a depender de `create_all` para cambios nuevos, esta migración inicial es la última vez que se arma "a mano".

**Importante:** no arrancar nunca la app apuntando a Neon *antes* de correr el paso 3. Si `crear_tablas()` llega a crear las tablas primero, el `alembic upgrade head` posterior va a fallar (Alembic no sabe que esas tablas ya existen si no las creó él).