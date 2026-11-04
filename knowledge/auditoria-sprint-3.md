# Revisión del Sprint 3 — 27 de octubre de 2026

## Alcance y fuentes

**Actualización posterior a la auditoría:** el usuario autorizó corregir las observaciones de Ruff y los marcadores del README. Se modernizaron anotaciones compatibles con Python 3.12+, se ordenaron imports, se retiraron imports sin uso y se limpiaron espacios. Las nueve observaciones restantes tras las correcciones automáticas se revisaron manualmente: ocho afectaban espacios en docstrings y una correspondía a la variable ambigua `l` de una prueba, renombrada a `log`. Ruff global ahora aprueba sin observaciones. El README conserva los enlaces de ambas versiones y ya no contiene marcadores de conflicto. Las tablas siguientes conservan los resultados históricos de la auditoría inicial.

Revisión del CSV `Pila_Sprint_3_Gestion_Envios.xlsm - Resumen Sprint 3.csv`, del código actual, de `AGENTS.md`, de los documentos de `knowledge/` y de los contratos y pruebas de `Back/`.

El CSV contiene un resumen por historia, dependencias y condiciones de cierre; no contiene los 45 ítems desglosados ni los criterios completos de las 13 historias. Las conclusiones funcionales se contrastan con los contratos y documentos del repositorio. Esta revisión no acredita aceptación por el equipo ni despliegue en producción.

La solicitud inicial autorizó completar el frontend de HU11/HU12 si ese era el único faltante y exigió consultar si había pendientes en otras HU. Tras comunicar los hallazgos, el usuario autorizó completar **HU04, HU06, HU11 y HU12**. Las tablas siguientes registran el diagnóstico inicial; los cambios posteriores y su verificación se documentan en [Reparto, recepción y seguimiento](reparto-terminal-seguimiento.md). Durante esa implementación no se modificó el backend. La limpieza posterior de Ruff sí actualizó su código, con autorización del usuario; no se modificaron archivos `.env`.

## Cobertura observada

| HU / bloque | Evidencia actual | Pendiente o límite |
| --- | --- | --- |
| HU07, inicio público de reclamo | `front/src/features/claims/`, integrado en seguimiento; contratos y pruebas de backend | El inicio público está implementado. No hay pantalla de gestión interna; es una capacidad adicional del backend y no un faltante demostrado del resultado público del CSV. |
| HU08, preguntas frecuentes | `front/src/features/faq/`, ruta pública y consulta filtrada de API | La consulta pública está implementada. El CRUD administrativo solo existe en backend; no se incorpora al alcance sin acordarlo. |
| HU10, gestión de recorridos | `front/src/features/routes/`, ruta privada, generación, edición, mapa, perfiles y alertas; pruebas de backend | Implementación presente; falta aceptación funcional en navegador y con servicios reales para declararla aceptada. |
| HU11, web móvil de reparto | Router `/api/v1/reparto/recorridos`, servicio, contratos y pruebas | No existe feature, ruta ni acceso para que REPARTIDOR consulte y opere sus recorridos. Faltan interfaz móvil, detalle y mapa, inicio y actualización de GPS con permisos y limpieza del seguimiento. |
| HU12, entrega a domicilio | Endpoints privados de contacto, entrega con firma y visita fallida, idempotencia y avisos por email | Faltan formularios del repartidor, contacto, captura de firma, datos del receptor y resultado de entrega/visita. Los reintentos deben conservar `operacion_id` y datos de la operación. |
| HU04, integración del seguimiento | Backend devuelve coordenadas de destino, historial y última ubicación pública del repartidor cuando corresponde | Los tipos y el servicio frontend omiten esos campos. La pantalla no tiene mapa ni historial real y conserva un aviso fijo de ubicación futura. |
| HU06, recepción en terminal | Backend con escaneo de solo lectura y recepción confirmada, autorización y pruebas | No existe pantalla, servicio frontend ni ruta para escanear/ingresar código, revisar el paquete y confirmar su recepción en una sucursal. Es una dependencia operativa de HU10: paquetes precargados no ingresan a recorridos hasta recibirse. |
| Cierre | Suite automatizada y documentación técnica disponibles | No se verificaron despliegue, aceptación de HU01–HU13, pruebas completas en navegador ni entrega real de email. El resumen CSV no basta para acreditarlos. |

### Error concreto en HU04

`getStatusStep` en `front/src/features/tracking/pages/TrackingPage.tsx` comprueba `normalizedStatus.includes('entreg')` antes de otros estados. Por ello, `ENTREGA_FALLIDA` activa visualmente la etapa de entrega completada. Se necesita un mapeo explícito de estados, incluyendo fallidos y estados finales de retiro; el texto del estado por sí solo no corrige la representación visual incorrecta.

### Diferencias documentales

- `knowledge/envios-seguimiento.md` conserva pendientes de backend que ya fueron implementados (HU05, HU06, HU10 y HU11/HU12). Debe actualizarse con el alcance finalmente acordado.
- El CSV menciona WhatsApp. La decisión posterior documentada en `Back/docs/04-historias-de-usuario/hu11-hu12-reparto.md` establece avisos solo por email. No se considera WhatsApp un faltante automático ni se incorpora una integración nueva. **Actualización:** esa decisión fue reemplazada; WhatsApp se implementó a pedido del usuario (ver [Sprint 2](sprint-2-notificaciones-retiro-y-neon.md)).
- `knowledge/README.md` ya estaba en conflicto de Git (`UU`) antes de esta revisión. `knowledge/estandares-codificacion.md` ya estaba sin seguimiento. Ambos se conservaron sin modificar.

## Validación de buenas prácticas

La referencia detallada es `knowledge/estandares-codificacion.md`, además de `AGENTS.md`. El CSV no incluye una lista propia de estándares de codificación.

| Criterio | Resultado observado |
| --- | --- |
| G1/G2, organización y responsabilidades | Features con páginas, hooks, servicios y tipos; backend separado en routers, servicios, contratos, reglas y repositorios. No se realizó una evaluación exhaustiva de cada función. |
| G3, configuración | Los servicios examinados usan `VITE_API_URL`. No se modificaron entornos ni se consultaron sus valores secretos. |
| G4, verificación estática | ESLint y build aprobados. Ruff global no cumple: 257 observaciones. |
| F1/F5, tipos y mapeos | Contratos API separados de modelos camelCase en los servicios examinados. Las comprobaciones de JSON son parciales; en seguimiento faltan campos funcionales del contrato actual. TypeScript no declara `strict`. |
| F2/F3, red y estado | Acceso HTTP en servicios; TanStack Query administra consultas y mutaciones. El store Redux registra únicamente sesión (`auth`). |
| F4, caché | Seguimiento usa clave con token y retiro invalida consultas relacionadas. HU11/HU12 deberán invalidar detalle, listado, ubicación y seguimiento afectados sin duplicar datos en Redux. |
| F6/F7, errores y acceso | Hay estados de carga y error y rutas bajo `ProtectedRoutes`. No hay rutas de repartidor ni terminal. En `trackingApi.ts`, el mensaje del payload se procesa antes del fallback de HTTP 500: conviene priorizar el mensaje genérico para errores internos. |
| F8/F9, interfaz y recursos | Tokens, lucide-react, labels y limpieza de mapas presentes. Blanco/negro explícitos en código de barras y estilos de impresión tienen un propósito documental. Accesibilidad a 320 px, teclado, firma táctil y GPS requieren validación en navegador; no se declaran aprobados por inspección. |
| B1–B8, backend | Routers delegan, contratos Pydantic, reglas puras y repositorios async presentes. Persisten imports directos de infraestructura en aplicación, por ejemplo en `servicio_empleados.py`, tal como reconoce el documento de estándares. No se acredita aislamiento estricto del ORM. |
| B9, pruebas | 377 pruebas aprobadas sumando la suite inicial y el reintento de las cuatro pruebas impedidas por permisos temporales. Proveedores de email simulados; no prueba entrega SMTP real. |

### Ruff global

Resultado de `.venv/Scripts/python.exe -m ruff check . --statistics` desde `Back/`:

| Regla | Cantidad |
| --- | ---: |
| UP045 | 135 |
| UP006 | 41 |
| UP035 | 26 |
| I001 | 19 |
| W293 | 11 |
| UP007 | 10 |
| F401 | 7 |
| UP017 | 3 |
| UP015 | 2 |
| E741, W292, W291 | 1 cada una |

Son principalmente modernización de anotaciones, orden de imports y espacios, además de imports sin usar y un nombre ambiguo. No equivalen a 257 fallos funcionales. No se aplicaron arreglos masivos durante la revisión.

## Comprobaciones ejecutadas

| Comando | Resultado |
| --- | --- |
| `npm run lint` desde `front/` | Aprobado. |
| `npm run build` desde `front/` | Aprobado al permitir creación de procesos fuera del sandbox; el primer intento falló con `spawn EPERM`. Advertencia de chunk principal mayor de 500 kB. |
| `.venv/Scripts/python.exe -m pip check` desde `Back/` | Sin dependencias rotas. |
| `.venv/Scripts/python.exe -m pytest -q` desde `Back/` | 373 aprobadas; 4 errores de preparación por acceso a carpeta temporal de Windows. |
| Reintento de `test_hu11_hu12_concurrencia.py` y `test_hu11_hu12_migracion.py` con `-p no:cacheprovider --basetemp=tests/.tmp-sprint3-audit-elevated-20261027`, fuera del sandbox | 4 aprobadas; 4 advertencias de Alembic por `path_separator`. Total de casos aprobados: 377. |
| Ruff global | 257 observaciones; salida no exitosa. |
| import-linter, también mediante el intérprete del entorno con `lint_imports(no_cache=True)` | Informa 2 contratos cumplidos y 99 archivos. Su resultado no acredita ausencia de los imports directos de infraestructura observados: hay una discrepancia entre cobertura del control y código que requiere revisar el propio control. |

## Alcance propuesto para acordar

El usuario aprobó completar HU11/HU12, la integración pendiente de HU04 y la pantalla de HU06; su frontend ya fue implementado y verificado. Posteriormente autorizó la limpieza global de Ruff y la resolución del README, ambas completadas. La gestión administrativa de reclamos/FAQ sigue fuera de ese conjunto. La discrepancia del control de imports sigue registrada como trabajo separado de calidad.

## Verificación de la limpieza de Ruff y del README

- Ruff global: sin observaciones, manteniendo las reglas configuradas.
- `pip check`: sin dependencias rotas.
- Suite completa del backend: **377 pruebas aprobadas**, con cuatro advertencias preexistentes de Alembic por `path_separator`. Se usó `-p no:cacheprovider --basetemp=tests/.tmp-ruff-cleanup-20261027` para aislar archivos temporales.
- Frontend: `npm run lint` y `npm run build` aprobados. Persiste la advertencia previa de Vite por un chunk mayor de 500 kB.
- OpenAPI: generado correctamente, con 45 rutas.
- Revisión de los 50 archivos Python modificados: cambios limitados a anotaciones, imports, limpieza documental y equivalencias previstas. Los cuerpos de las funciones de migración permanecen iguales.
- README: diez enlaces locales válidos, sin marcadores de conflicto. `git diff --check` aprobado.
