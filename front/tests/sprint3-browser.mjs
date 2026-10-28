// Smoke de navegador sin dependencias externas. Requiere Vite en 5173 y Chrome con CDP en 9227.
// Los contratos HTTP y el GPS se simulan; no envía datos a servicios reales.
import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'

const tabs = await (await fetch('http://127.0.0.1:9227/json')).json()
const tab = tabs.find((item) => item.type === 'page')
const socket = new WebSocket(tab.webSocketDebuggerUrl)
await new Promise((resolve) => socket.addEventListener('open', resolve, { once: true }))
let sequence = 0
const pending = new Map()
socket.addEventListener('message', ({ data }) => {
  const message = JSON.parse(data)
  if (!message.id) return
  const entry = pending.get(message.id)
  if (!entry) return
  pending.delete(message.id)
  if (message.error) entry.reject(new Error(message.error.message))
  else entry.resolve(message.result)
})
function cdp(method, params = {}) {
  return new Promise((resolve, reject) => { const id = ++sequence; pending.set(id, { resolve, reject }); socket.send(JSON.stringify({ id, method, params })) })
}
async function evaluate(expression) {
  const result = await cdp('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text + ': ' + result.exceptionDetails.exception?.description)
  return result.result.value
}
async function waitFor(expression) {
  const deadline = Date.now() + 20000
  while (Date.now() < deadline) {
    if (await evaluate(expression)) return
    await new Promise((resolve) => setTimeout(resolve, 150))
  }
  throw new Error('Tiempo agotado: ' + expression + '\n' + await evaluate('document.body.innerText'))
}
async function click(text) {
  await evaluate(`(() => { const button = [...document.querySelectorAll('button')].find(item => item.textContent.trim() === ${JSON.stringify(text)}); if (!button || button.disabled) throw new Error('Botón no disponible: ' + ${JSON.stringify(text)}); button.click(); })()`)
}
async function fill(id, value) {
  await evaluate(`(() => { const input = document.getElementById(${JSON.stringify(id)}); const type = input instanceof HTMLSelectElement ? HTMLSelectElement : input instanceof HTMLTextAreaElement ? HTMLTextAreaElement : HTMLInputElement; Object.getOwnPropertyDescriptor(type.prototype, 'value').set.call(input, ${JSON.stringify(value)}); input.dispatchEvent(new Event(input instanceof HTMLSelectElement ? 'change' : 'input', { bubbles: true })); })()`)
}
async function navigate(path) {
  await cdp('Page.navigate', { url: `http://127.0.0.1:5173${path}` })
  await waitFor('Boolean(window.__mockReady && document.querySelector("#root")?.children.length)')
}
async function screenshot(name) {
  const { data } = await cdp('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
  await writeFile(`node_modules/.tmp/sprint3-${name}.png`, Buffer.from(data, 'base64'))
}
function mockApi() {
  const role = new URLSearchParams(location.search).get('testRole') || (location.pathname.startsWith('/terminal') ? 'VENDEDOR' : 'REPARTIDOR')
  localStorage.setItem('gestion-envios.auth-session', JSON.stringify({ token: 'test-session', user: { id: 'driver-1', name: 'Repartidor de prueba', dni: '12345678', email: 'prueba@example.test', role, requiresPasswordChange: false } }))
  const long = location.search.includes('long=true')
  const branch = { id: 1, nombre: 'Sucursal Centro', direccion: 'Centro 123', ciudad: 'Córdoba', provincia: 'Córdoba', latitud: -31.4, longitud: -64.18 }
  const item = { paquete_id: 'package-1', numero_paquete: 'PAQ-ABCDEFGHIJ', orden: 1, descripcion: 'Libros', peso_kg: 2, estado: 'EN_SUCURSAL_ORIGEN', estado_en_recorrido: 'PENDIENTE', token_seguimiento: 'ENV-ABCDEFGHIJ', destinatario_nombre: 'Ana Gómez', destinatario_telefono: '123456' }
  const route = { id: 'route-1', fecha: new Date().toISOString().slice(0, 10), tipo_distancia: long ? 'LARGA' : 'CORTA', estado: 'GENERADO', generado_automaticamente: true, sucursal_origen_id: 1, sucursal_origen_nombre: branch.nombre, repartidor: { usuario_id: 'driver-1', nombre: 'Repartidor de prueba', telefono: '123456' }, cantidad_paradas: 1, cantidad_paquetes: 1, distancia_estimada_km: 2, duracion_estimada_min: 10, created_at: new Date().toISOString(), updated_at: new Date().toISOString(), orientacion_calles_grados: 0, vuelve_a_sucursal: !long, sucursal_origen: branch, paradas: [{ orden: 1, tipo_parada: long ? 'SUCURSAL' : 'DOMICILIO', destino: 'Domicilio de prueba 123', latitud: -31.41, longitud: -64.19, paquetes: [item] }], trazado: [], paquetes_sin_ubicacion: 0 }
  const state = window.__mock = { route, item, position: null, deliveries: [], receptions: [], gpsCleared: 0, received: false, unexpected: [], notificationRetries: 0 }
  const originalFetch = window.fetch.bind(window)
  const ok = (data, extra = {}) => new Response(JSON.stringify({ status: 'success', data, ...extra }), { status: 200, headers: { 'Content-Type': 'application/json' } })
  window.fetch = async (input, init = {}) => {
    const url = typeof input === 'string' ? input : input.url
    if (!url.includes('/api/v1/')) return originalFetch(input, init)
    const path = new URL(url, location.origin).pathname.replace('/api/v1', '')
    const body = init.body ? JSON.parse(init.body) : null
    if (path === '/auth/login-token') return ok({ token: 'test-session', user: { id: 'driver-1', nombre: 'Usuario de prueba', dni: '12345678', email: 'prueba@example.test', rol: role, requiere_cambio_password: false } })
    if (path === '/sucursales') return ok([branch])
    if (path.startsWith('/terminal/paquetes/') && path.endsWith('/escanear')) return ok({ ...item, largo_cm: 10, ancho_cm: 10, alto_cm: 10, estado_actual: state.received ? 'EN_SUCURSAL_ORIGEN' : 'Pendiente', disponible_para_recepcion: !state.received, motivo_no_disponible: state.received ? 'El paquete ya fue recibido.' : null, observaciones: null, envio: { token_seguimiento: item.token_seguimiento, remitente_nombre: 'Juan Pérez', remitente_documento: '12345678', destinatario_nombre: item.destinatario_nombre, destino: 'Domicilio 123' } })
    if (path.endsWith('/recepcionar')) { state.received = true; state.receptions.push(body); return ok({ numero_paquete: item.numero_paquete, estado: 'EN_SUCURSAL_ORIGEN', sucursal_nombre: branch.nombre, fecha_hora_recepcion: new Date().toISOString(), token_seguimiento: item.token_seguimiento }) }
    if (path === '/reparto/recorridos') return ok([route])
    if (path === '/reparto/recorridos/route-1') return ok(route)
    if (path.endsWith('/iniciar')) { route.estado = 'EN_CURSO'; item.estado = long ? 'EN_TRANSITO' : 'EN_REPARTO'; return ok(route) }
    if (path.endsWith('/ubicacion')) {
      if (init.method === 'PUT') { state.position = { ...body, actualizado_at: new Date().toISOString() }; if (long) { item.estado = 'EN_SUCURSAL_DESTINO'; item.estado_en_recorrido = 'ENTREGADO'; route.estado = 'FINALIZADO' } }
      return ok(state.position, { paquetes_actualizados: long && state.position ? ['package-1'] : [] })
    }
    if (path.endsWith('/contacto')) return ok({ destinatario_nombre: item.destinatario_nombre, telefono: null, telefono_disponible: false })
    if (path.endsWith('/entrega') || path.endsWith('/visita-fallida')) {
      state.deliveries.push(body)
      if (state.deliveries.length === 1) throw new TypeError('Simulación de respuesta perdida')
      route.estado = 'FINALIZADO'; item.estado = path.endsWith('/entrega') ? 'ENTREGADO' : 'ENTREGA_FALLIDA'; item.estado_en_recorrido = path.endsWith('/entrega') ? 'ENTREGADO' : 'FALLIDO'
      return ok({ evento_id: 'receipt-1', paquete_id: item.paquete_id, resultado: path.endsWith('/entrega') ? 'EXITOSO' : 'FALLIDO', receptor_nombre: body.receptor_nombre ?? null, firma_disponible: !!body.firma_base64, fecha_hora: new Date().toISOString() })
    }
    if (path.endsWith('/notificaciones') || path.endsWith('/notificaciones/reintentar')) {
      if (path.endsWith('/reintentar')) state.notificationRetries += 1
      const now = new Date().toISOString()
      const notification = (id, canal, destinatario_tipo, destino, failed) => ({ id, motivo: 'NUEVO_ENVIO', canal, destinatario_tipo, destino, estado: failed && !state.notificationRetries ? 'FALLIDO' : 'ENVIADO', error_detalle: failed && !state.notificationRetries ? 'El teléfono registrado no es un número válido para WhatsApp.' : null, created_at: now, updated_at: now })
      return ok({ token_seguimiento: item.token_seguimiento, notificaciones: [notification('n1', 'EMAIL', 'REMITENTE', 'juan@example.test', false), notification('n2', 'WHATSAPP', 'DESTINATARIO', '+5493564000000', true)] })
    }
    if (path.startsWith('/sucursales/opciones-retiro/')) return ok({ token_seguimiento: 'ENV-SUCURSAL01', tipo_entrega: 'sucursal', aplica_retiro: true, motivo_no_aplica: null, sucursal_asignada: { ...branch, es_sucursal_asignada: true }, sucursales_disponibles: [], paquetes: [{ numero_paquete: item.numero_paquete, descripcion: 'Libros', estado: 'LISTO_PARA_RETIRO', disponible_para_retirar: true }], requisitos_retiro: { titular: 'Documento original.', tercero_autorizado: 'Autorización y copias.' } })
    if (path === '/seguimiento/ENV-SUCURSAL01') return ok({ token_seguimiento: 'ENV-SUCURSAL01', tipo_entrega: 'sucursal', destino: 'Sucursal Centro', latitud_destino: null, longitud_destino: null, paquetes: [{ ...item, estado: 'LISTO_PARA_RETIRO', fecha_registro: new Date().toISOString(), ultima_actualizacion: new Date().toISOString(), historial: [], ubicacion_repartidor: null }] })
    if (path.startsWith('/seguimiento/')) return ok({ token_seguimiento: item.token_seguimiento, destino: 'Domicilio de prueba 123', latitud_destino: -31.41, longitud_destino: -64.19, paquetes: [{ ...item, estado: 'ENTREGA_FALLIDA', fecha_registro: new Date().toISOString(), ultima_actualizacion: new Date().toISOString(), historial: [{ estado_anterior: 'EN_REPARTO', estado: 'ENTREGA_FALLIDA', fecha_hora: new Date().toISOString(), descripcion: 'Visita no completada' }], ubicacion_repartidor: null }] })
    state.unexpected.push(path)
    return new Response(JSON.stringify({ status: 'error', message: 'Mock no definido' }), { status: 404 })
  }
  Object.defineProperty(navigator, 'geolocation', { configurable: true, value: { watchPosition(success, error) { window.__gps = success; window.__gpsError = error; return 1 }, clearWatch() { state.gpsCleared++ } } })
  window.__mockReady = true
}
try {
  await mkdir('node_modules/.tmp', { recursive: true })
  await cdp('Page.enable')
  await cdp('Runtime.enable')
  await cdp('Emulation.setDeviceMetricsOverride', { width: 320, height: 850, deviceScaleFactor: 1, mobile: true })
  await cdp('Page.addScriptToEvaluateOnNewDocument', { source: `(${mockApi.toString()})()` })
  await navigate('/terminal/recepcion')
  await waitFor('Boolean(document.getElementById("terminal-code"))')
  await fill('terminal-code', '  paq-abcde fghij ')
  await click('Identificar paquete')
  await waitFor('document.body.innerText.includes("Juan Pérez")')
  assert.equal(await evaluate('window.__mock.receptions.length'), 0, 'escanear no recibe automáticamente')
  await fill('terminal-branch', '1')
  await click('Confirmar recepción física')
  await waitFor('document.body.innerText.includes("recibido en Sucursal Centro")')
  assert.equal(await evaluate('window.__mock.receptions.length'), 1)
  assert.equal(await evaluate('document.documentElement.scrollWidth <= innerWidth'), true, 'recepción a 320 px')
  assert.equal(await evaluate('document.getElementById("terminal-code").value'), '', 'el código queda vacío para el siguiente escaneo')
  await screenshot('terminal-320')
  console.log('HU06: escaneo, confirmación separada, sucursal y 320 px aprobados')
  await waitFor('document.body.innerText.includes("No enviado")')
  await click('Reenviar avisos no enviados')
  await waitFor('window.__mock.notificationRetries === 1 && !document.body.innerText.includes("No enviado")')
  console.log('HU05: estado por canal y reenvío de avisos aprobados')

  await navigate('/seguimiento?token=ENV-ABCDEFGHIJ')
  await waitFor('document.body.innerText.includes("La visita no pudo completarse")')
  assert.equal(await evaluate('document.querySelectorAll(".tracking-step.is-complete").length < 4'), true)
  await evaluate('document.querySelector(".tracked-package__history-button").click()')
  await waitFor('Boolean(document.querySelector("dialog.modal[open] .tracking-history"))')
  assert.equal(await evaluate('document.querySelector("dialog.modal[open]").innerText.includes("Visita no completada")'), true)
  await evaluate('document.querySelector("dialog.modal[open] .modal__close").click()')
  assert.equal(await evaluate('Boolean(document.querySelector(".location-map .leaflet-marker-icon"))'), true)
  await screenshot('tracking-320')
  console.log('HU04: mapa, historial real y visita fallida aprobados')

  await navigate('/seguimiento?token=ENV-SUCURSAL01')
  await waitFor('document.body.innerText.includes("Ya podés pasar a retirar")')
  assert.equal(await evaluate('document.body.innerText.includes("Para retirar")'), true)
  assert.equal(await evaluate('document.documentElement.scrollWidth <= innerWidth'), true, 'retiro a 320 px')
  await screenshot('tracking-pickup-320')
  console.log('HU09: sucursal de retiro y disponibilidad en el seguimiento aprobados')

  await navigate('/reparto')
  await waitFor('document.body.innerText.includes("Abrir recorrido")')
  await click('Abrir recorrido'); await waitFor('document.body.innerText.includes("Iniciar recorrido")')
  await click('Iniciar recorrido'); await click('Confirmar inicio')
  await waitFor('document.body.innerText.includes("Activar ubicación GPS")')
  await click('Activar ubicación GPS')
  await waitFor('typeof window.__gps === "function"')
  await evaluate('window.__gps({ coords: { latitude: -31.4, longitude: -64.18 } })')
  await waitFor('Boolean(window.__mock.position)')
  await click('Registrar entrega o visita')
  await waitFor('document.body.innerText.includes("No hay teléfono disponible")')
  await fill('receiver-name', 'Ana Gómez'); await fill('receiver-document', '30111222'); await fill('receiver-birthdate', '2000-01-01')
  await evaluate(`(() => { const canvas = document.querySelector('canvas'); const rect = canvas.getBoundingClientRect(); for (const [type,x,y] of [['pointerdown',20,20],['pointermove',60,45],['pointerup',90,40]]) canvas.dispatchEvent(new PointerEvent(type, { pointerId: 1, clientX: rect.left+x, clientY: rect.top+y, bubbles: true })); })()`)
  await click('Confirmar entrega')
  await waitFor('document.body.innerText.includes("Reintentar la misma operación")')
  await click('Reintentar la misma operación')
  await waitFor('document.body.innerText.includes("Entrega y firma registradas")')
  const requests = await evaluate('window.__mock.deliveries')
  assert.equal(requests.length, 2); assert.deepEqual(requests[0], requests[1], 'idempotencia conserva UUID, firma y todos los datos')
  assert.ok(requests[0].firma_base64.startsWith('iVBOR'))
  await writeFile('node_modules/.tmp/sprint3-signature.png', Buffer.from(requests[0].firma_base64, 'base64'))
  await waitFor('window.__mock.gpsCleared > 0')
  assert.equal(await evaluate('document.documentElement.scrollWidth <= innerWidth'), true, 'reparto a 320 px')
  await screenshot('delivery-320')
  console.log('HU11/HU12 corta: inicio, GPS, contacto ausente, firma, reintento idéntico y cierre del GPS aprobados')

  await navigate('/reparto')
  await waitFor('document.body.innerText.includes("Abrir recorrido")'); await click('Abrir recorrido')
  await waitFor('document.body.innerText.includes("Iniciar recorrido")'); await click('Iniciar recorrido'); await click('Confirmar inicio')
  await waitFor('document.body.innerText.includes("Activar ubicación GPS")'); await click('Activar ubicación GPS')
  await waitFor('typeof window.__gpsError === "function"'); await evaluate('window.__gpsError({code: 1})')
  await waitFor('document.body.innerText.includes("Permiso de ubicación denegado")')
  assert.equal(await evaluate('window.__mock.gpsCleared > 0'), true)
  await click('Registrar entrega o visita'); await waitFor('Boolean(document.getElementById("delivery-mode"))')
  await fill('delivery-mode', 'failed'); await fill('failure-reason', 'No se encontró al destinatario')
  await click('Confirmar visita fallida'); await waitFor('document.body.innerText.includes("Reintentar la misma operación")')
  await click('Reintentar la misma operación'); await waitFor('document.body.innerText.includes("Visita fallida registrada")')
  const failedRequests = await evaluate('window.__mock.deliveries')
  assert.deepEqual(failedRequests[0], failedRequests[1])
  assert.equal(failedRequests[0].motivo_fallo, 'No se encontró al destinatario')
  assert.equal('firma_base64' in failedRequests[0], false)
  await evaluate('document.documentElement.dataset.theme = "dark"')
  assert.equal(await evaluate('document.documentElement.scrollWidth <= innerWidth'), true)
  await screenshot('failed-dark-320')
  console.log('HU12: visita fallida, reintento idéntico, aviso email sin promesa de entrega y GPS denegado aprobados')

  await navigate('/reparto?long=true')
  await waitFor('document.body.innerText.includes("Abrir recorrido")'); await click('Abrir recorrido')
  await waitFor('document.body.innerText.includes("Iniciar recorrido")'); await click('Iniciar recorrido'); await click('Confirmar inicio')
  await waitFor('document.body.innerText.includes("Activar ubicación GPS")'); await click('Activar ubicación GPS')
  await waitFor('typeof window.__gps === "function"'); await evaluate('window.__gps({ coords: { latitude: -31.41, longitude: -64.19 } })')
  await waitFor('document.body.innerText.includes("Recorrido finalizado")')
  assert.equal(await evaluate('window.__mock.gpsCleared > 0'), true)
  console.log('HU11 larga: llegada automática reflejada y GPS detenido al finalizar')

  await navigate('/reparto?testRole=VENDEDOR')
  await waitFor('location.pathname === "/unauthorized"')
  console.log('Autorización: VENDEDOR no accede al reparto')
} finally { socket.close() }
