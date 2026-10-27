import { IDBFactory } from 'fake-indexeddb'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { IncidentCreatePage } from './IncidentCreatePage'
import { useIncidentSynchronization } from '../hooks/useIncidentSynchronization'
import { listIncidents, loadIncidentDraft, saveIncidentDraft } from '../services/incidentStorage'
import { getDriverItinerary } from '../services/driverItinerary'
import { saveItinerary } from '../services/offlineStorage'
import { newIncidentDraft } from '../domain/incident'
import type { IncidentDraft } from '../domain/incident'

vi.mock('../services/driverItinerary', async original => ({
  ...await original<typeof import('../services/driverItinerary')>(), getDriverItinerary: vi.fn(),
}))
const ownerId = '123e4567-e89b-42d3-a456-426614174005'
const stopId = '123e4567-e89b-42d3-a456-426614174006'
function ConnectedForm() {
  useIncidentSynchronization(ownerId)
  return <MemoryRouter><IncidentCreatePage ownerId={ownerId} /></MemoryRouter>
}
async function mount(connected = false) {
  const view = render(connected ? <ConnectedForm /> : <MemoryRouter><IncidentCreatePage ownerId={ownerId} /></MemoryRouter>)
  await waitFor(() => expect(screen.getByLabelText('Tipo')).toBeEnabled())
  return view
}
async function fill() {
  fireEvent.change(screen.getByLabelText('Tipo'), { target: { value: 'AVERIA' } })
  fireEvent.click(screen.getByRole('radio', { name: /Alta/ }))
  fireEvent.click(screen.getByRole('button', { name: 'Usar mi ubicación' }))
  await screen.findByText('Ubicación del dispositivo seleccionada.')
}
beforeEach(() => {
  vi.stubGlobal('indexedDB', new IDBFactory())
  vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
  vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(true)
  vi.stubGlobal('fetch', vi.fn().mockImplementation((_url, init: RequestInit) => {
    const body = JSON.parse(init.body as string) as { operation_id: string }
    return Promise.resolve(new Response(JSON.stringify({ operation_id: body.operation_id,
      incidencia_id: stopId, estado: 'PENDIENTE_VALIDACION', registrada_en: new Date().toISOString() }), { status: 201 }))
  }))
  Object.defineProperty(navigator, 'geolocation', { configurable: true, value: {
    getCurrentPosition: vi.fn((success: PositionCallback) => success({ coords: { latitude: -12.04, longitude: -77.03 } } as GeolocationPosition)),
  } })
  vi.mocked(getDriverItinerary).mockReset().mockResolvedValue([])
})
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.unstubAllEnvs() })

it('ruta dorada: envío válido muestra acuse e ID del servidor', async () => {
  await mount(true); await fill()
  fireEvent.click(screen.getByRole('button', { name: 'Enviar incidencia' }))
  expect(await screen.findByText(/Incidencia registrada · pendiente de validación/)).toBeInTheDocument()
  expect(await loadIncidentDraft(ownerId)).toBeUndefined()
  expect(fetch).toHaveBeenCalledTimes(1)
  expect(screen.getByLabelText('Hora (automática)')).toHaveAttribute('readonly')
})
it('ruta feliz: restaura el borrador al volver y cuenta Unicode', async () => {
  const view = await mount()
  fireEvent.change(screen.getByLabelText('Observación (opcional)'), { target: { value: '😀'.repeat(500) } })
  expect(screen.getByText('500/500 caracteres')).toBeInTheDocument()
  await waitFor(async () => expect((await loadIncidentDraft(ownerId))?.observacion).toHaveLength(1000))
  view.unmount(); await mount()
  expect(screen.getByLabelText('Observación (opcional)')).toHaveValue('😀'.repeat(500))
})
it('ruta infeliz: faltantes llevan foco al primer error y conservan el borrador', async () => {
  await mount()
  fireEvent.click(screen.getByRole('button', { name: 'Enviar incidencia' }))
  expect(screen.getByLabelText('Tipo')).toHaveFocus()
  expect(screen.getByText('Selecciona el tipo de incidencia.')).toBeInTheDocument()
  expect(screen.getByText('Selecciona la severidad.')).toBeInTheDocument()
  await waitFor(async () => expect(await loadIncidentDraft(ownerId)).toBeDefined())
  expect(await listIncidents(ownerId)).toEqual([])
  expect(fetch).not.toHaveBeenCalled()
})
it('ruta infeliz: 403 conserva el reporte y ofrece reintento explícito', async () => {
  vi.mocked(fetch).mockResolvedValue(new Response('{}', { status: 403 }))
  await mount(true); await fill()
  fireEvent.click(screen.getByRole('button', { name: 'Enviar incidencia' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('la sesión no tiene permiso')
  const operation = (await listIncidents(ownerId))[0].payload.operation_id
  await userEvent.click(screen.getByRole('button', { name: 'Reintentar envíos pendientes' }))
  expect((await listIncidents(ownerId))[0].payload.operation_id).toBe(operation)
})
it('ruta de borde: offline, recarga y reconexión confirman una sola operación', async () => {
  vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(false)
  const view = await mount(true); await fill()
  fireEvent.click(screen.getByRole('button', { name: 'Enviar incidencia' }))
  await screen.findByRole('heading', { name: 'Mis envíos' })
  const [pending] = await listIncidents(ownerId)
  expect(fetch).not.toHaveBeenCalled()
  view.unmount(); await mount(true)
  expect(await screen.findByText(/Pendiente de envío · se sincronizará/)).toBeInTheDocument()
  vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(true)
  act(() => { window.dispatchEvent(new Event('online')) })
  await screen.findByText(/Incidencia registrada · pendiente de validación/)
  const sent = JSON.parse(vi.mocked(fetch).mock.calls[0][1]?.body as string) as { operation_id: string }
  expect(sent.operation_id).toBe(pending.payload.operation_id)
  expect(fetch).toHaveBeenCalledTimes(1)
})
it('ruta de borde: GPS rechazado permite seleccionar parada propia con coordenadas', async () => {
  Object.defineProperty(navigator, 'geolocation', { configurable: true, value: {
    getCurrentPosition: (_success: PositionCallback, error: PositionErrorCallback) => error({ code: 1 } as GeolocationPositionError),
  } })
  await saveItinerary({ ownerId, savedAt: Date.now(), expiresAt: Date.now() + 60_000,
    stops: [{ stopId, position: 1, status: 'EN_RUTA', location: { latitud: -12, longitud: -77 } }] })
  await mount()
  fireEvent.click(screen.getByRole('button', { name: 'Usar mi ubicación' }))
  expect(await screen.findByText(/Puedes continuar con una parada/)).toBeInTheDocument()
  await userEvent.selectOptions(screen.getByLabelText('Parada actual'), stopId)
  fireEvent.change(screen.getByLabelText('Tipo'), { target: { value: 'OTRO' } })
  fireEvent.click(screen.getByRole('radio', { name: /Baja/ }))
  fireEvent.click(screen.getByRole('button', { name: 'Enviar incidencia' }))
  await waitFor(async () => expect((await listIncidents(ownerId))[0].payload.parada_id).toBe(stopId))
})
it('ruta infeliz: almacenamiento bloqueado no confirma encolado', async () => {
  await mount(); await fill()
  vi.stubGlobal('indexedDB', { open: () => { throw new Error('cuota') } })
  fireEvent.click(screen.getByRole('button', { name: 'Enviar incidencia' }))
  expect(await screen.findByText(/No se pudo guardar la incidencia/)).toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: 'Mis envíos' })).not.toBeInTheDocument()
})
it('ruta de borde: teclado, validación al salir y observación de 501 caracteres', async () => {
  await mount()
  const user = userEvent.setup()
  screen.getByLabelText('Tipo').focus()
  await user.tab()
  expect(screen.getByText('Selecciona el tipo de incidencia.')).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Observación (opcional)'), { target: { value: 'x'.repeat(501) } })
  fireEvent.blur(screen.getByLabelText('Observación (opcional)'))
  expect(screen.getByText('La observación admite hasta 500 caracteres.')).toBeInTheDocument()
})
it('ruta feliz: borrador de otra cuenta no se muestra', async () => {
  await saveIncidentDraft(stopId, { ...newIncidentDraft(), observacion: 'Borrador de otra cuenta' })
  await mount()
  expect(screen.getByLabelText('Observación (opcional)')).toHaveValue('')
})
it('ruta infeliz: 422 permite corregir sin cambiar la operación', async () => {
  vi.mocked(fetch).mockResolvedValueOnce(new Response('{}', { status: 422 }))
  await mount(true); await fill()
  fireEvent.click(screen.getByRole('button', { name: 'Enviar incidencia' }))
  await screen.findByRole('alert')
  const operation = (await listIncidents(ownerId))[0].payload.operation_id
  fireEvent.click(screen.getByRole('button', { name: 'Corregir datos conservando el identificador' }))
  fireEvent.change(screen.getByLabelText('Observación (opcional)'), { target: { value: 'Dato corregido' } })
  fireEvent.click(screen.getByRole('button', { name: 'Enviar incidencia' }))
  await screen.findByText(/Incidencia registrada · pendiente de validación/)
  expect((await listIncidents(ownerId))[0].payload.operation_id).toBe(operation)
  expect(await listIncidents(ownerId)).toHaveLength(1)
})

it.each([
  ['tipo', { tipo: '' }, 'Selecciona el tipo de incidencia.'],
  ['severidad', { severidad: '' }, 'Selecciona la severidad.'],
  ['ubicación', { ubicacion: null }, 'Usa tu ubicación o selecciona una parada con coordenadas.'],
  ['hora', { ocurrida_en: '' }, 'La hora del dispositivo está adelantada. Revisa su reloj antes de crear otro reporte.'],
  ['varios', { tipo: '', severidad: '', ubicacion: null }, 'Selecciona el tipo de incidencia.'],
] satisfies [string, Partial<IncidentDraft>, string][])(
  'I04 ruta infeliz: falta %s, conserva borrador tras recargar sin encolar ni enviar',
  async (_field, changes, message) => {
    const draft: IncidentDraft = { ...newIncidentDraft(), tipo: 'AVERIA', severidad: 'ALTA',
      ubicacion: { latitud: -12, longitud: -77 }, observacion: 'Borrador sintético I04', ...changes }
    await saveIncidentDraft(ownerId, draft)
    const view = await mount(true)
    fireEvent.click(screen.getByRole('button', { name: 'Enviar incidencia' }))
    expect(screen.getByText(message)).toBeInTheDocument()
    await waitFor(async () => expect(await loadIncidentDraft(ownerId)).toEqual(draft))
    view.unmount()
    await mount(true)
    expect(screen.getByLabelText('Observación (opcional)')).toHaveValue(draft.observacion)
    expect(await loadIncidentDraft(ownerId)).toEqual(draft)
    expect(await listIncidents(ownerId)).toEqual([])
    expect(fetch).not.toHaveBeenCalled()
  },
)

it.each([
  ['I05 hora futura', { ocurrida_en: new Date(Date.now() + 3_600_000).toISOString() }, 'ocurrida_en'],
  ['I06 observación Unicode de 501 caracteres', { observacion: '😀'.repeat(501) }, 'observacion'],
] satisfies [string, Partial<IncidentDraft>, string][])(
  '%s ruta infeliz: rechaza envío y conserva el valor íntegro tras recargar',
  async (_scenario, changes, field) => {
    const draft: IncidentDraft = { ...newIncidentDraft(), tipo: 'AVERIA', severidad: 'ALTA',
      ubicacion: { latitud: -12, longitud: -77 }, ...changes }
    await saveIncidentDraft(ownerId, draft)
    const view = await mount(true)
    fireEvent.click(screen.getByRole('button', { name: 'Enviar incidencia' }))
    expect(document.getElementById(`${field}-error`)).toBeInTheDocument()
    await waitFor(async () => expect(await loadIncidentDraft(ownerId)).toEqual(draft))
    view.unmount()
    await mount(true)
    expect(await loadIncidentDraft(ownerId)).toEqual(draft)
    expect(screen.getByLabelText('Observación (opcional)')).toHaveValue(draft.observacion)
    expect(await listIncidents(ownerId)).toEqual([])
    expect(fetch).not.toHaveBeenCalled()
  },
)

it('I11 ruta infeliz: conflicto visible conserva operación sin corrección ni reintento automático', async () => {
  vi.mocked(fetch).mockResolvedValue(new Response('{}', { status: 409 }))
  const view = await mount(true); await fill()
  fireEvent.click(screen.getByRole('button', { name: 'Enviar incidencia' }))
  await screen.findByRole('alert')
  const [original] = await listIncidents(ownerId)
  expect(original.errorStatus).toBe(409)
  view.unmount(); await mount(true)
  expect(await screen.findByRole('alert')).toHaveTextContent('conflicto')
  act(() => { window.dispatchEvent(new Event('online')) })
  expect(screen.queryByRole('button', { name: 'Corregir datos conservando el identificador' })).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Reintentar envíos pendientes' })).not.toBeInTheDocument()
  await waitFor(async () => expect(await listIncidents(ownerId)).toEqual([original]))
  expect(fetch).toHaveBeenCalledTimes(1)
})
