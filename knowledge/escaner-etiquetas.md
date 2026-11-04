# Escáner con el celular e impresión de etiquetas

Corresponde a HU15 (admisión y control en la sucursal), del Sprint 2.

## El celular como escáner

Basado en el escáner del administrador de stock de Tekron:

- **Motor de lectura:** `BarcodeDetector` nativo si existe; si no, ZXing (CODE_128 y QR), que se carga solo cuando hace falta.
- **Cámara:** se abre la trasera y se apaga siempre al cerrar el modal. La linterna aparece donde el navegador la ofrece.
- **Lectura:** el mismo código se ignora durante 2,5 s.
- **Aviso de lectura** (`shared/services/scanFeedback.ts`): pitido limpio y agudo de lector de caja (2.900 Hz, 90 ms) y vibración breve si el código se acepta; zumbido grave (180 Hz, 300 ms) y vibración doble si se rechaza. Se eligieron entre muestras. Vale para el celular y la cámara de la PC. El sonido es un WAV generado en el navegador y reproducido con `<audio>` (en iPhone, Web Audio queda mudo con la tecla de silencio). Se habilita en el toque que abre la cámara. Safari no tiene `navigator.vibrate`: en iOS 18 o posterior se usa el toque háptico del interruptor (`<input type="checkbox" switch>`); en versiones anteriores solo suena.
- **Sin lecturas repetidas:** con la cámara abierta, un código ya aceptado se rechaza («ya se escaneó»). Recepción en terminal rechaza el paquete ya identificado o ya recibido en la visita; retiro, el que se está completando o ya se registró (leerlo de nuevo borraba el formulario). Si la consulta anterior falló, se puede volver a leer para reintentar.
- **Modos:** único (retiro en sucursal) o continuo (recepción en terminal, con lista de los últimos leídos).
- **Repartidor:** «Escanear paquete» en recorridos de corta distancia en curso. Si el paquete corresponde, abre el registro de entrega o visita; si no, explica por qué.
- **Contexto seguro:** exige HTTPS o `localhost`. Para probar desde un celular en la red local: `HTTPS_DEV=true npm run dev`, que activa un certificado autofirmado y expone el servidor en la red.

## Impresión de etiquetas

Perfiles tomados de Soderia ERP, en `front/src/shared/printing/printerProfiles.ts`:

| Impresora | Tamaños |
|---|---|
| Zebra ZD220 y térmica genérica | 50×25, 40×30 mm |
| SATO CG408 / WS4 | 50×25, 40×30, 50×100, 100×50 mm |
| Brother QL-800 | 62×29, 29×90 mm |
| Etiqueta de envío | 100×150 mm (4×6") |
| Hoja común | A4 |

- **Diseños:** las etiquetas chicas llevan código de barras Code 128 y número; desde 50×100 llevan todos los datos del envío.
- **Cómo se imprime:** desde un `iframe` oculto con `@page { size; margin: 0 }`. La impresora se elige en el diálogo del navegador, y su driver debe tener el mismo tamaño de papel.
- **Configuración:** impresora, tamaño y copias (1 a 10). Se guarda por puesto con la clave `gestion-envios.impresion`.
- **Quién imprime:** la sucursal, al admitir el paquete. El cliente no imprime etiquetas térmicas: recibe un comprobante que puede mostrar en el celular.
- **Dónde está:**
  - en la recepción en terminal, con impresión automática al admitir (casilla recordada por puesto) e «Imprimir etiqueta» o «Reimprimir etiqueta» en cada paquete;
  - en el resultado del registro, solo para el personal («Imprimir etiquetas (mostrador)»);
  - en la trazabilidad del monitor («Imprimir etiqueta»).
