import test from 'node:test'
import assert from 'node:assert/strict'
import { getStatusStep } from '../src/features/tracking/trackingStatus.ts'
import { receiverIsOldEnough } from '../src/features/delivery/deliveryValidation.ts'

test('una visita fallida nunca representa una entrega completada', () => {
  assert.equal(getStatusStep('ENTREGA_FALLIDA'), 2)
  for (const status of ['ENTREGADO', 'ENTREGADO_EN_SUCURSAL', 'RETIRADO']) assert.equal(getStatusStep(status), 3)
})
test('los estados desconocidos y pendientes no se presentan como entregados', () => {
  assert.equal(getStatusStep('Pendiente'), 0)
  assert.equal(getStatusStep('NUEVO_ESTADO'), 0)
  assert.equal(getStatusStep('EN_SUCURSAL_DESTINO'), 1)
  assert.equal(getStatusStep('EN_REPARTO'), 2)
})
test('la edad respeta el límite estricto del contrato de entrega', () => {
  assert.equal(receiverIsOldEnough('2010-10-27', '2026-10-27'), false)
  assert.equal(receiverIsOldEnough('2010-10-26', '2026-10-27'), true)
  assert.equal(receiverIsOldEnough('2010-10-28', '2026-10-27'), false)
  assert.equal(receiverIsOldEnough('2027-01-01', '2026-10-27'), false)
  assert.equal(receiverIsOldEnough('1900-01-01', '2026-10-27'), false)
  assert.equal(receiverIsOldEnough('1906-10-27', '2026-10-27'), true)
})
test('fecha inválida y cumpleaños de año bisiesto', () => {
  assert.equal(receiverIsOldEnough('', '2026-10-27'), false)
  assert.equal(receiverIsOldEnough('2001-02-29', '2026-10-27'), false)
  assert.equal(receiverIsOldEnough('2008-02-29', '2024-02-29'), false)
  assert.equal(receiverIsOldEnough('2008-02-29', '2024-03-01'), true)
})
