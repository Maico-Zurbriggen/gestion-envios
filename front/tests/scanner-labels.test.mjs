import test from 'node:test'
import assert from 'node:assert/strict'
import { PACKAGE_CODE_PATTERN, TRACKING_TOKEN_PATTERN, checkScannedCode, isRepeatedRead, normalizeScannedCode } from '../src/shared/services/scannedCode.ts'
import { canRegisterDelivery, findScannedDelivery } from '../src/features/delivery/deliveryValidation.ts'
import {
  DEFAULT_PRINT_SETTINGS,
  PRINTER_PROFILES,
  clampCopies,
  getLabelLayout,
  normalizePrintSettings,
  resolveLabelSize,
} from '../src/shared/printing/printerProfiles.ts'
import { buildShipmentLabelsHtml, expandCopies, getPieceText } from '../src/shared/printing/shipmentLabels.ts'
import { escapeHtml } from '../src/shared/printing/printHtml.ts'

test('los códigos leídos se normalizan a mayúsculas y sin espacios', () => {
  assert.equal(normalizeScannedCode('  paq-abc 123 def4\n'), 'PAQ-ABC123DEF4')
  assert.equal(normalizeScannedCode('\t'), '')
})

test('solo se aceptan paquetes con el formato PAQ- y diez caracteres', () => {
  assert.deepEqual(checkScannedCode('paq-4d8r2m7kq1', PACKAGE_CODE_PATTERN), { valid: true, code: 'PAQ-4D8R2M7KQ1' })
  assert.deepEqual(checkScannedCode('PAQ-4D8R2M7KQ', PACKAGE_CODE_PATTERN), { valid: false, code: 'PAQ-4D8R2M7KQ', reason: 'pattern' })
  assert.deepEqual(checkScannedCode('PAQ-4D8R2M7KQ12', PACKAGE_CODE_PATTERN).valid, false)
  assert.deepEqual(checkScannedCode('ENV-7K2Q9XWB4M', PACKAGE_CODE_PATTERN).valid, false)
  assert.deepEqual(checkScannedCode('PAQ-4D8R2M7K_1', PACKAGE_CODE_PATTERN).valid, false)
  assert.deepEqual(checkScannedCode('   ', PACKAGE_CODE_PATTERN), { valid: false, code: '', reason: 'empty' })
  assert.equal(TRACKING_TOKEN_PATTERN.test('env-7k2q9xwb4m'), true)
  assert.deepEqual(checkScannedCode('cualquier cosa'), { valid: true, code: 'CUALQUIERCOSA' })
})

test('la misma lectura se ignora durante 2,5 segundos', () => {
  const last = { code: 'PAQ-AAAAAAAAAA', at: 10_000 }
  assert.equal(isRepeatedRead('PAQ-AAAAAAAAAA', null, 10_000), false)
  assert.equal(isRepeatedRead('PAQ-AAAAAAAAAA', last, 12_499), true)
  assert.equal(isRepeatedRead('PAQ-AAAAAAAAAA', last, 12_500), false)
  assert.equal(isRepeatedRead('PAQ-BBBBBBBBBB', last, 10_100), false)
})

const route = (overrides = {}) => ({
  distanceType: 'CORTA',
  status: 'EN_CURSO',
  stops: [
    { type: 'DOMICILIO', packages: [
      { code: 'PAQ-AAAAAAAAAA', routeStatus: 'PENDIENTE', status: 'EN_REPARTO' },
      { code: 'PAQ-BBBBBBBBBB', routeStatus: 'ENTREGADO', status: 'ENTREGADO' },
      { code: 'PAQ-CCCCCCCCCC', routeStatus: 'PENDIENTE', status: 'EN_SUCURSAL_DESTINO' },
    ] },
    { type: 'SUCURSAL', packages: [{ code: 'PAQ-DDDDDDDDDD', routeStatus: 'PENDIENTE', status: 'EN_REPARTO' }] },
  ],
  ...overrides,
})

test('el escaneo del repartidor abre solo paradas pendientes habilitadas', () => {
  const current = route()
  assert.equal(findScannedDelivery(current, 'paq-aaaaaaaaaa').kind, 'enabled')
  assert.equal(findScannedDelivery(current, 'PAQ-ZZZZZZZZZZ').kind, 'not-in-route')
  assert.equal(findScannedDelivery(current, 'PAQ-BBBBBBBBBB').reason, 'already-visited')
  assert.equal(findScannedDelivery(current, 'PAQ-CCCCCCCCCC').reason, 'not-in-delivery')
  assert.equal(findScannedDelivery(current, 'PAQ-DDDDDDDDDD').reason, 'branch-stop')
  assert.equal(findScannedDelivery(route({ distanceType: 'LARGA' }), 'PAQ-AAAAAAAAAA').reason, 'route-not-active')
  assert.equal(findScannedDelivery(route({ status: 'GENERADO' }), 'PAQ-AAAAAAAAAA').reason, 'route-not-active')
})

test('el botón y el escaneo usan la misma regla de habilitación', () => {
  const current = route()
  for (const stop of current.stops) {
    for (const item of stop.packages) {
      assert.equal(canRegisterDelivery(current, stop, item), findScannedDelivery(current, item.code).kind === 'enabled')
    }
  }
})

test('los perfiles de impresora son los de Soderia más 4x6 y A4', () => {
  const sizes = Object.fromEntries(PRINTER_PROFILES.map((profile) => [profile.id, profile.sizes.map((size) => `${size.widthMm}x${size.heightMm}`)]))
  assert.deepEqual(sizes, {
    zebra_zd220: ['50x25', '40x30'],
    sato: ['50x25', '40x30', '50x100', '100x50'],
    brother_ql800: ['62x29', '90x29'],
    shipping_4x6: ['100x150'],
    a4: ['210x297'],
  })
})

test('el diseño de la etiqueta se adapta al tamaño del papel', () => {
  const variantOf = (profileId, sizeId) => getLabelLayout(resolveLabelSize({ profileId, sizeId, copies: 1 }))
  for (const [profile, size] of [['zebra_zd220', '50x25'], ['zebra_zd220', '40x30'], ['brother_ql800', '62x29'], ['brother_ql800', '29x90']]) {
    assert.equal(variantOf(profile, size).variant, 'compact', `${profile} ${size}`)
  }
  for (const [profile, size] of [['sato', '50x100'], ['sato', '100x50'], ['shipping_4x6', '100x150'], ['a4', 'a4']]) {
    assert.equal(variantOf(profile, size).variant, 'full', `${profile} ${size}`)
  }
  assert.equal(variantOf('sato', '100x50').orientation, 'landscape')
  assert.equal(variantOf('sato', '50x100').orientation, 'portrait')
  const a4 = variantOf('a4', 'a4')
  assert.equal(a4.pageWidthMm, 210)
  assert.ok(a4.labelWidthMm < a4.pageWidthMm)
})

test('la configuración guardada se corrige si está incompleta o fuera de rango', () => {
  assert.deepEqual(normalizePrintSettings(null), DEFAULT_PRINT_SETTINGS)
  assert.deepEqual(normalizePrintSettings({ profileId: 'sato', sizeId: '100x50', copies: 3 }), { profileId: 'sato', sizeId: '100x50', copies: 3 })
  assert.deepEqual(normalizePrintSettings({ profileId: 'zebra_zd220', sizeId: '100x50', copies: 50 }), { profileId: 'zebra_zd220', sizeId: '50x25', copies: 10 })
  assert.deepEqual(normalizePrintSettings({ profileId: 'inexistente', copies: '0' }), { profileId: 'a4', sizeId: 'a4', copies: 1 })
  assert.equal(clampCopies('2.7'), 2)
  assert.equal(clampCopies('abc'), 1)
})

const sampleLabel = {
  packageNumber: 'PAQ-AAAAAAAAAA',
  trackingToken: 'ENV-BBBBBBBBBB',
  recipientName: '<script>alert("x")</script> & Cía',
  destination: 'Calle <b>falsa</b> 123',
  deliveryType: 'domicilio',
  weightKg: 2,
  dimensions: '10 × 20 × 30 cm',
  index: 2,
  total: 3,
  date: '28/10/26',
  dateCaption: 'Registrado',
}

test('las etiquetas escapan los datos y usan el tamaño de página configurado', () => {
  const layout = getLabelLayout(resolveLabelSize({ profileId: 'shipping_4x6', sizeId: '100x150', copies: 1 }))
  const html = buildShipmentLabelsHtml([sampleLabel], layout, 2, (value) => `<svg data-value="${value}"></svg>`)
  assert.ok(html.includes('@page { size: 100mm 150mm; margin: 0; }'))
  assert.ok(!html.includes('<script>'))
  assert.ok(html.includes(escapeHtml(sampleLabel.recipientName)))
  assert.ok(html.includes('Calle &lt;b&gt;falsa&lt;/b&gt; 123'))
  assert.ok(html.includes('Gestión de Envíos'))
  assert.ok(html.includes('Paquete 2 de 3'))
  assert.ok(html.includes('ENV-BBBBBBBBBB'))
  assert.equal(html.match(/class="page"/g).length, 2)
})

test('la etiqueta chica lleva solo código de barras, número y n/m', () => {
  const layout = getLabelLayout(resolveLabelSize({ profileId: 'zebra_zd220', sizeId: '50x25', copies: 1 }))
  const html = buildShipmentLabelsHtml([sampleLabel], layout, 1, () => '<svg></svg>')
  assert.ok(html.includes('@page { size: 50mm 25mm; margin: 0; }'))
  assert.ok(html.includes('2/3'))
  assert.ok(!html.includes('Gestión de Envíos'))
  assert.ok(!html.includes('falsa'))
  assert.equal(getPieceText({ index: null, total: null }, 'full'), '')
  assert.deepEqual(expandCopies(['a', 'b'], 2), ['a', 'a', 'b', 'b'])
})
