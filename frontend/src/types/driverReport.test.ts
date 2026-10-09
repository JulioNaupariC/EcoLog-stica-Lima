import { createPendingReport, validateReport, validUuid } from './driverReport'
const owner = '123e4567-e89b-42d3-a456-426614174000'
const stop = '223e4567-e89b-42d3-a456-426614174000'

describe('ST-032 reportes', () => {
  it('crea evento con UUID, sin información personal de cliente', () => {
    const report = createPendingReport(owner, stop, 'ENTREGADO')
    expect(validUuid(report.operationId)).toBe(true)
    expect(report.attemptCount).toBe(0)
    expect(Object.keys(report).sort()).toEqual(['attemptCount','createdAt','operationId','ownerId','status','stopId'].sort())
  })
  it('rechaza propietario y parada inválidos', () => {
    expect(() => createPendingReport('INVALIDO', stop, 'ENTREGADO')).toThrow()
    expect(() => createPendingReport(owner, 'INVALIDO', 'ENTREGADO')).toThrow()
  })
  it('rechaza intentos negativos y estados inválidos', () => {
    const report = createPendingReport(owner, stop, 'ENTREGADO')
    expect(() => validateReport({ ...report, attemptCount: -1 })).toThrow()
    expect(() => validateReport({ ...report, status: 'CUALQUIERA' as never })).toThrow()
  })
})
