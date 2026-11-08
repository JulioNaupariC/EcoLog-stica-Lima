import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import raw from '../test/fixtures/rutas/sostenibilidad-con-datos.json'
import empty from '../test/fixtures/rutas/sostenibilidad-sin-datos.json'
import { parseSustainability } from '../domain/sustainability'
import type { Period, Sustainability } from '../domain/sustainability'
import { SustainabilityError } from '../services/sustainability'
import type { SustainabilitySource } from '../services/sustainability'
import { SustainabilityPage } from './SustainabilityPage'

vi.mock('../domain/operationRoutes', async original => ({ ...await original<typeof import('../domain/operationRoutes')>(), operationDateInLima: () => '2026-11-20' }))
let source: SustainabilitySource
const data = (period: Period) => parseSustainability({ ...raw, periodo: period }, period)
beforeEach(() => { source = { load: vi.fn().mockImplementation((p: Period) => Promise.resolve(data(p))) } })
function show() { const expired = vi.fn(); return { ...render(<SustainabilityPage source={source} onSessionExpired={expired} />), expired } }
const loaded = () => screen.findByRole('table')
const submit = () => fireEvent.click(screen.getByRole('button', { name: 'Consultar periodo' }))
const choose = (from: string, to: string) => {
  fireEvent.change(screen.getByLabelText('Desde'), { target: { value: from } })
  fireEvent.change(screen.getByLabelText('Hasta'), { target: { value: to } })
}

it('D01 muestra el periodo aplicado, unidades y tabla accesible con el fixture ST-045', async () => {
  show(); const table = await loaded()
  expect(screen.getByText(/01\/11\/2026 — 20\/11\/2026/)).toBeInTheDocument()
  expect(screen.getByText('Datos de prueba')).toBeInTheDocument()
  expect(within(table).getByRole('columnheader', { name: 'Secuencial' })).toBeInTheDocument()
  for (const unit of ['km', 'kg CO₂', 'L', 'S/']) expect(within(table).getAllByText(new RegExp(` ${unit.replace('/', '\\/')}$`)).length).toBeGreaterThan(0)
  expect(screen.getByText('SIMULADO-2026-11')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: /EN-008/ })).toHaveAttribute('href', expect.stringContaining('ECL-26'))
  expect(screen.getByRole('heading', { name: 'Equivalente ambiental: No disponible' })).toBeInTheDocument()
})
it('D01 representa la referencia BDD 150 km, ahorro 50 km y 25 %, cumplimiento 75 %', async () => {
  vi.mocked(source.load).mockImplementation(p => Promise.resolve(parseSustainability({ ...raw, periodo: p, rutas_cerradas: 2,
    distancia_km: 150, co2_kg: 30, combustible_l: 15, costo_soles: 240,
    ahorro_vs_secuencial: { distancia_km: 50, co2_kg: 10, combustible_l: 5, costo_soles: 80, pct: 25 }, cumplimiento_ventanas_pct: 75 }, p)))
  show(); const table = await loaded()
  expect(within(table).getByRole('cell', { name: '150 km' })).toBeInTheDocument()
  expect(within(table).getByRole('cell', { name: '200 km' })).toBeInTheDocument()
  expect(within(table).getByRole('cell', { name: '50 km' })).toBeInTheDocument()
  expect(screen.getByText('25 %')).toBeInTheDocument(); expect(screen.getByText('75 %')).toBeInTheDocument()
})
it('D06 vacío explícito sin métricas, ceros inventados ni tabla vacía', async () => {
  vi.mocked(source.load).mockImplementation(p => Promise.resolve(parseSustainability({ ...empty, periodo: p }, p)))
  show()
  expect(await screen.findByRole('heading', { name: 'Sin datos para este periodo' })).toBeInTheDocument()
  expect(screen.queryByRole('table')).not.toBeInTheDocument()
  expect(screen.queryByText('0 km')).not.toBeInTheDocument()
})
it('D04 fechas invertidas o ausentes anuncian validación y enfocan Desde sin petición', async () => {
  show(); await loaded()
  choose('2026-11-21', '2026-11-20'); submit()
  expect(screen.getByRole('alert')).toHaveTextContent('Desde debe ser anterior o igual a Hasta')
  expect(screen.getByLabelText('Desde')).toHaveFocus()
  expect(screen.getByLabelText('Hasta')).toHaveAttribute('aria-invalid', 'true')
  expect(screen.queryByRole('table')).not.toBeInTheDocument()
  choose('', '2026-11-20'); submit(); expect(source.load).toHaveBeenCalledOnce()
})
it('filtros editados no cambian el periodo aplicado hasta consultar; se envían con teclado', async () => {
  const user = userEvent.setup(); show(); await loaded()
  choose('2026-11-08', '2026-11-08')
  expect(screen.getByText(/01\/11\/2026 — 20\/11\/2026/)).toBeInTheDocument()
  screen.getByRole('button', { name: 'Consultar periodo' }).focus(); await user.keyboard('{Enter}')
  await waitFor(() => expect(screen.getByText(/08\/11\/2026 — 08\/11\/2026/)).toBeInTheDocument())
  expect(source.load).toHaveBeenLastCalledWith({ desde: '2026-11-08', hasta: '2026-11-08' }, expect.any(AbortSignal))
})
it.each(['forbidden', 'invalid_period', 'unavailable'] as const)('error %s no se presenta como periodo sin datos y admite reintento', async kind => {
  vi.mocked(source.load).mockRejectedValueOnce(new SustainabilityError(kind))
  show(); expect(await screen.findByRole('alert')).toBeInTheDocument()
  expect(screen.queryByText('Sin datos para este periodo')).not.toBeInTheDocument()
  submit(); await loaded()
})
it('401 devuelve al flujo de autenticación', async () => {
  vi.mocked(source.load).mockRejectedValueOnce(new SustainabilityError('unauthorized'))
  const { expired } = show(); await waitFor(() => expect(expired).toHaveBeenCalledOnce())
  expect(screen.queryByRole('table')).not.toBeInTheDocument()
})
it('D06 muestra ceros verdaderos, base cero y aumentos negativos sin ocultarlos', async () => {
  vi.mocked(source.load).mockImplementation(p => Promise.resolve(parseSustainability({ ...raw, periodo: p,
    distancia_km: 0, ahorro_vs_secuencial: { ...raw.ahorro_vs_secuencial, distancia_km: 0, pct: null }, cumplimiento_ventanas_pct: null }, p)))
  show(); await loaded()
  expect(screen.getAllByText('0 km').length).toBeGreaterThan(0)
  expect(screen.getByText('No calculable (base secuencial cero)')).toBeInTheDocument()
  expect(screen.getByText('No disponible')).toBeInTheDocument()
  vi.mocked(source.load).mockImplementation(p => Promise.resolve(parseSustainability({ ...raw, periodo: p,
    distancia_km: 150, ahorro_vs_secuencial: { ...raw.ahorro_vs_secuencial, distancia_km: -100, pct: -200 } }, p)))
  submit(); await loaded(); expect(screen.getByText('-200 %')).toBeInTheDocument()
  expect(screen.getByText('-100 km')).toBeInTheDocument()
})
it('no etiqueta como simulada una respuesta real y conserva versiones múltiples', async () => {
  vi.mocked(source.load).mockImplementation(p => Promise.resolve({ ...data(p), simulado: false, parametros_versiones: ['HIST-1', 'HIST-2'] }))
  show(); await loaded(); expect(screen.queryByText('Datos de prueba')).not.toBeInTheDocument()
  expect(screen.getByText('HIST-1')).toBeInTheDocument(); expect(screen.getByText('HIST-2')).toBeInTheDocument()
})
it('descarta respuestas fuera de orden y aborta al desmontar', async () => {
  let resolve!: (value: Sustainability) => void
  vi.mocked(source.load).mockImplementationOnce(() => new Promise(done => { resolve = done }))
  const rendered = show(); await waitFor(() => expect(source.load).toHaveBeenCalledOnce())
  const firstSignal = vi.mocked(source.load).mock.calls[0][1]
  choose('2026-11-08', '2026-11-08'); submit(); await loaded()
  await act(async () => { resolve(data(raw.periodo)); await Promise.resolve() })
  expect(firstSignal.aborted).toBe(true)
  expect(screen.getByText(/08\/11\/2026 — 08\/11\/2026/)).toBeInTheDocument()
  const lastSignal = vi.mocked(source.load).mock.calls[1][1]
  rendered.unmount(); expect(lastSignal.aborted).toBe(true)
})
it('un error inesperado no divulga mensajes internos', async () => {
  vi.mocked(source.load).mockRejectedValueOnce(new Error('PRIVATE_DETAIL'))
  show(); expect(await screen.findByRole('alert')).not.toHaveTextContent('PRIVATE_DETAIL')
})
