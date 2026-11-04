import test from 'node:test'
import assert from 'node:assert/strict'
import { requiresBranch, resolveActiveBranch, shouldChooseBranch } from '../src/features/auth/branchAccess.ts'

const centro = { id: 1, name: 'Centro', city: 'Córdoba', province: 'Córdoba', address: 'X 1', active: true }
const norte = { id: 2, name: 'Norte', city: 'Rosario', province: 'Santa Fe', address: 'Y 2', active: true }

test('el repartidor no elige sucursal; el resto del personal sí', () => {
  assert.equal(requiresBranch('REPARTIDOR'), false)
  for (const role of ['VENDEDOR', 'ADMINISTRATIVO', 'SUPERADMIN']) assert.equal(requiresBranch(role), true)
  assert.equal(requiresBranch(null), false)
})

test('se mantiene la sucursal anterior solo si sigue habilitada', () => {
  assert.equal(resolveActiveBranch([centro, norte], 2), 2)
  assert.equal(resolveActiveBranch([centro, norte], 9), null, 'una sucursal quitada no queda activa')
  assert.equal(resolveActiveBranch([centro], null), 1, 'con una sola entra directo')
  assert.equal(resolveActiveBranch([], 1), null)
})

test('después del login pregunta solo si tiene más de una sucursal', () => {
  const user = { id: 'u', name: 'Ana', dni: '1', email: null, role: 'VENDEDOR', requiresPasswordChange: false, branches: [centro, norte] }
  assert.equal(shouldChooseBranch(user), true)
  assert.equal(shouldChooseBranch({ ...user, branches: [centro] }), false)
  assert.equal(shouldChooseBranch({ ...user, role: 'REPARTIDOR' }), false)
})
