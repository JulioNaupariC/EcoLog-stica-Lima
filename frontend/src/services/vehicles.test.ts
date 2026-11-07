import { createVehicle, listVehicles, VehicleServiceError } from './vehicles'
import type { VehicleCreatePayload, VehicleResponse } from './vehicles'

const payload: VehicleCreatePayload = {
  placa: ' abc-123 ',
  tipo: 'CAMIONETA',
  capacidad_kg: '1000.00',
  capacidad_m3: '8.00',
  rendimiento_km_l: '10.000',
  factor_co2_kg_km: '0.30000',
  anio_fabricacion: 2024,
}

const vehicle: VehicleResponse = {
  ...payload,
  vehiculo_id: '123e4567-e89b-12d3-a456-426614174000',
  placa: 'ABC-123',
  estado: 'ACTIVO',
}

function jsonResponse(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

function page(items: unknown[], total = items.length) {
  return { items, page: 1, page_size: 100, total }
}

function respond(body: unknown, status: number) {
  const fetchMock = vi.fn().mockResolvedValue(jsonResponse(body, status))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

const operations = [
  { name: 'GET', call: () => listVehicles(), success: 200, response: page([vehicle]) },
  { name: 'POST', call: () => createVehicle(payload), success: 201, response: vehicle },
] as const

describe('servicio vehicles', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.test/v1')
  })

  afterEach(() => {
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
  })

  it('GET pide una página de 100 con URL base y credenciales; conserva orden e inactivos', async () => {
    const rows = [
      { ...vehicle, placa: 'ZZZ-123', estado: 'INACTIVO' },
      { ...vehicle, vehiculo_id: '223e4567-e89b-12d3-a456-426614174000' },
    ]
    const fetchMock = respond(page(rows, 2), 200)
    await expect(listVehicles()).resolves.toEqual(rows)
    expect(fetchMock).toHaveBeenCalledExactlyOnceWith('https://api.example.test/v1/vehiculos?page=1&page_size=100', {
      method: 'GET', credentials: 'include',
    })
  })

  it('GET acepta página vacía', async () => {
    respond(page([]), 200)
    await expect(listVehicles()).resolves.toEqual([])
  })

  it('POST envía solo siete campos, conserva strings y placa original, acepta 201', async () => {
    const fetchMock = respond(vehicle, 201)
    const extra = { ...payload, estado: 'INACTIVO', vehiculo_id: 'not-sent', extra: 'not-sent' }
    await expect(createVehicle(extra)).resolves.toEqual(vehicle)
    expect(fetchMock).toHaveBeenCalledExactlyOnceWith('https://api.example.test/v1/vehiculos', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
  })

  it.each(['CAMIONETA', 'FURGON', 'MOTO'] as const)('valida tipo %s y mantiene estado string abierto', async (tipo) => {
    const expected = { ...vehicle, tipo, estado: 'MANTENIMIENTO', factor_co2_kg_km: '0E-5' }
    respond({ ...expected, extra: 'discarded' }, 201)
    await expect(createVehicle({ ...payload, tipo })).resolves.toEqual(expected)
  })

  it.each([null, {}, { vehicles: [] }, 'vehicles', [vehicle], { items: null }, page([vehicle, null])])('GET rechaza página o elemento inválido: %j', async (body) => {
    respond(body, 200)
    await expect(listVehicles()).rejects.toBeInstanceOf(VehicleServiceError)
  })

  const invalidRows: unknown[] = [
    null, [], 'vehicle',
    { ...vehicle, vehiculo_id: 42 },
    { ...vehicle, vehiculo_id: 'invalid' },
    { ...vehicle, placa: null },
    { ...vehicle, tipo: 'AUTO' },
    { ...vehicle, capacidad_kg: 1000 },
    { ...vehicle, capacidad_m3: 'NaN' },
    { ...vehicle, rendimiento_km_l: 'Infinity' },
    { ...vehicle, factor_co2_kg_km: {} },
    { ...vehicle, anio_fabricacion: '2024' },
    { ...vehicle, anio_fabricacion: 2024.5 },
    { ...vehicle, estado: false },
  ]

  describe.each(operations)('$name', ({ name, call, success, response }) => {
    it.each(invalidRows)('rechaza vehículo incompatible: %j', async (body) => {
      respond(name === 'GET' ? page([body]) : body, success)
      await expect(call()).rejects.toMatchObject({ kind: 'unexpected' })
    })

    it.each([
      [401, 'unauthorized', 'Tu sesión no está disponible o ha vencido.'],
      [403, 'forbidden', 'No tienes permisos para realizar esta acción.'],
      [503, 'unavailable', 'El servicio no está disponible en este momento.'],
      [500, 'unexpected', 'No se pudo completar la operación.'],
      [404, 'unexpected', 'No se pudo completar la operación.'],
    ] as const)('mapea HTTP %s sin exponer contenido', async (status, kind, message) => {
      respond({ detail: 'private-server-detail' }, status)
      const error: unknown = await call().catch((caught: unknown) => caught)
      expect(error).toBeInstanceOf(VehicleServiceError)
      expect(error).toMatchObject({ kind, status, message, issues: [] })
      expect(JSON.stringify(error)).not.toContain('private-server-detail')
    })

    it('rechaza un status de éxito incorrecto', async () => {
      const status = success === 200 ? 201 : 200
      respond(response, status)
      await expect(call()).rejects.toMatchObject({ kind: 'unexpected', status })
    })

    it('rechaza éxito sin JSON', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('invalid-json', { status: success })))
      await expect(call()).rejects.toMatchObject({ kind: 'unexpected' })
    })

    it('conserva la categoría HTTP aunque el cuerpo no sea JSON', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('private', { status: 503 })))
      await expect(call()).rejects.toMatchObject({ kind: 'unavailable', status: 503 })
    })

    it('distingue error de red sin exponer su mensaje', async () => {
      vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('private transport detail')))
      const error: unknown = await call().catch((caught: unknown) => caught)
      expect(error).toMatchObject({ kind: 'network', message: 'No se pudo comunicar con el servicio.' })
      expect(String(error)).not.toContain('private transport detail')
    })

    it('no ejecuta fetch con URL base inválida', async () => {
      vi.stubEnv('VITE_API_BASE_URL', 'ftp://invalid.test')
      const fetchMock = vi.fn()
      vi.stubGlobal('fetch', fetchMock)
      await expect(call()).rejects.toMatchObject({ kind: 'unexpected' })
      expect(fetchMock).not.toHaveBeenCalled()
    })
  })

  it('POST 409 significa placa duplicada', async () => {
    respond({ detail: 'private' }, 409)
    await expect(createVehicle(payload)).rejects.toMatchObject({
      kind: 'conflict', status: 409, message: 'La placa ya está registrada.',
    })
  })

  it.each([409, 422])('GET %s no representa conflicto de placa ni validación del formulario', async (status) => {
    respond({ detail: [{ loc: ['body', 'placa'] }] }, status)
    await expect(listVehicles()).rejects.toMatchObject({ kind: 'unexpected', status, issues: [] })
  })

  it('422 reconoce solo loc exacto, deduplica campos y sustituye todos los detalles por mensajes propios', async () => {
    const fields = Object.keys(payload)
    respond({
      detail: [
        ...fields.map((field) => ({ loc: ['body', field], msg: 'private', input: 'private', ctx: { private: true } })),
        { loc: ['body', 'placa'], msg: { private: true } },
        { loc: ['body', 'estado'], msg: 'private' },
        { loc: ['query', 'placa'], msg: 'private' },
        { loc: ['body', 'nested', 'placa'], msg: 'private' },
        { loc: ['body', '__proto__'], msg: 'private' },
        { loc: ['body', 'constructor'], msg: 'private' },
        { loc: ['body', 0], msg: 'private' },
        { loc: ['body'], msg: 'private' },
        { loc: 'body', msg: 'private' },
        null, [],
      ],
    }, 422)
    const error: unknown = await createVehicle(payload).catch((caught: unknown) => caught)
    expect(error).toMatchObject({
      kind: 'validation', status: 422, message: 'Revisa los datos ingresados.',
      issues: [
        { field: 'placa', message: 'Revisa la placa.' },
        { field: 'tipo', message: 'Selecciona un tipo de vehículo válido.' },
        { field: 'capacidad_kg', message: 'Revisa la capacidad en kg.' },
        { field: 'capacidad_m3', message: 'Revisa la capacidad en m³.' },
        { field: 'rendimiento_km_l', message: 'Revisa el rendimiento en km/L.' },
        { field: 'factor_co2_kg_km', message: 'Revisa el factor CO₂ en kg/km.' },
        { field: 'anio_fabricacion', message: 'Revisa el año de fabricación.' },
      ],
    })
    expect(JSON.stringify(error)).not.toMatch(/private|input|ctx|msg/u)
  })

  it.each([null, [], {}, { detail: 'private' }, { detail: [{ loc: ['body', 'unknown'] }] }])(
    '422 desconocido o malformado conserva un mensaje general seguro', async (body) => {
      respond(body, 422)
      await expect(createVehicle(payload)).rejects.toMatchObject({
        kind: 'validation', message: 'Revisa los datos ingresados.', issues: [],
      })
    },
  )
})
