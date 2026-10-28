// Verifica que las páginas públicas conserven el menú lateral cuando hay sesión.
// Requiere Vite en 5173 y Chrome con CDP en 9227; la API se simula en la página.
import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'

const tab = (await (await fetch('http://127.0.0.1:9227/json')).json()).find((item) => item.type === 'page')
const socket = new WebSocket(tab.webSocketDebuggerUrl)
await new Promise((resolve) => socket.addEventListener('open', resolve, { once: true }))
let sequence = 0
const pending = new Map()
socket.addEventListener('message', ({ data }) => {
  const message = JSON.parse(data)
  const entry = message.id && pending.get(message.id)
  if (!entry) return
  pending.delete(message.id)
  if (message.error) entry.reject(new Error(message.error.message)); else entry.resolve(message.result)
})
const cdp = (method, params = {}) => new Promise((resolve, reject) => { const id = ++sequence; pending.set(id, { resolve, reject }); socket.send(JSON.stringify({ id, method, params })) })
const evaluate = async (expression) => (await cdp('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })).result.value
async function waitFor(expression) {
  const deadline = Date.now() + 20000
  while (Date.now() < deadline) { if (await evaluate(expression)) return; await new Promise((r) => setTimeout(r, 150)) }
  throw new Error(`Tiempo agotado: ${expression}\nURL: ${await evaluate('location.href')}\n${await evaluate('document.body.innerText.slice(0, 600)')}`)
}
async function screenshot(name) {
  const { data } = await cdp('Page.captureScreenshot', { format: 'png' })
  await mkdir('node_modules/.tmp', { recursive: true })
  await writeFile(`node_modules/.tmp/${name}.png`, Buffer.from(data, 'base64'))
}
function mockApi() {
  const ok = (data) => new Response(JSON.stringify({ status: 'success', data }), { status: 200, headers: { 'Content-Type': 'application/json' } })
  localStorage.setItem('gestion-envios.auth-session', JSON.stringify({ token: 'test-session', user: { id: 'u1', name: 'Admin General', dni: '00000000', email: 'a@example.test', role: 'SUPERADMIN', requiresPasswordChange: false } }))
  const originalFetch = window.fetch.bind(window)
  window.fetch = async (input, init = {}) => {
    const url = typeof input === 'string' ? input : input.url
    if (!url.includes('/api/v1/')) return originalFetch(input, init)
    const path = new URL(url, location.origin).pathname.replace('/api/v1', '')
    if (path === '/auth/login-token' || path === '/auth/me') return ok({ token: 'test-session', user: { id: 'u1', nombre: 'Admin General', dni: '00000000', email: 'a@example.test', rol: 'SUPERADMIN', requiere_cambio_password: false } })
    if (path === '/sucursales') return ok([{ id: 1, nombre: 'Sucursal Centro', provincia: 'Córdoba', ciudad: 'Córdoba', direccion: 'Av. Colón 1', latitud: -31.4, longitud: -64.18 }])
    if (path.startsWith('/preguntas-frecuentes')) return ok([])
    return ok({})
  }
}
await cdp('Page.enable')
await cdp('Emulation.setDeviceMetricsOverride', { width: 1366, height: 900, deviceScaleFactor: 1, mobile: false })
const { identifier } = await cdp('Page.addScriptToEvaluateOnNewDocument', { source: `(${mockApi.toString()})()` })
const hasSidebar = 'Boolean(document.querySelector("aside.app-sidebar"))'
for (const [path, name] of [['/', 'inicio'], ['/envios/nuevo', 'registrar-envio'], ['/seguimiento', 'seguir-envio'], ['/preguntas-frecuentes', 'faq'], ['/sucursales', 'sucursales']]) {
  await cdp('Page.navigate', { url: `http://localhost:5173${path}` })
  await waitFor('Boolean(document.querySelector("main, .app-content__body > *"))')
  await new Promise((r) => setTimeout(r, 600))
  assert.equal(await evaluate(hasSidebar), true, `${path}: debería mostrar el menú lateral con sesión`)
  assert.equal(await evaluate('Boolean(document.querySelector(".public-header"))'), false, `${path}: sin encabezado público duplicado`)
  await screenshot(`panel-${name}`)
}
// Navegar con clics del menú, como un usuario.
await cdp('Page.navigate', { url: 'http://localhost:5173/' })
await waitFor(hasSidebar)
for (const label of ['Registrar envío', 'Seguir envío', 'Recibir paquetes', 'Registrar envío', 'Inicio']) {
  await evaluate(`[...document.querySelectorAll('aside.app-sidebar a')].find((a) => a.textContent.trim() === ${JSON.stringify(label)}).click()`)
  await new Promise((r) => setTimeout(r, 500))
  assert.equal(await evaluate(hasSidebar), true, `después de ir a ${label}`)
}
console.log('Con sesión: el menú lateral se mantiene en todas las secciones')

// Sin sesión, las páginas públicas siguen sueltas con su encabezado.
await cdp('Page.removeScriptToEvaluateOnNewDocument', { identifier })
await evaluate("localStorage.removeItem('gestion-envios.auth-session')")
await cdp('Page.navigate', { url: 'http://localhost:5173/seguimiento' })
await waitFor('Boolean(document.querySelector("main"))')
console.log('Sin sesión (seguimiento):', await evaluate(hasSidebar) ? 'CON menú' : 'página pública sin menú')
socket.close()
