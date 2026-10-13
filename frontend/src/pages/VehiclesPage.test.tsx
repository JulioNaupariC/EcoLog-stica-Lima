import { StrictMode } from 'react'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createVehicle, listVehicles, VehicleServiceError } from '../services/vehicles'
import type { VehicleResponse } from '../services/vehicles'
import { VehiclesPage } from './VehiclesPage'

vi.mock('../services/vehicles', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../services/vehicles')>()
  return { ...actual, createVehicle: vi.fn(), listVehicles: vi.fn() }
})

const createMock = vi.mocked(createVehicle)
const listMock = vi.mocked(listVehicles)
const vehicle: VehicleResponse = {
  vehiculo_id: '123e4567-e89b-12d3-a456-426614174000',
  placa: 'ABC-123', tipo: 'CAMIONETA',
  capacidad_kg: '1000.00', capacidad_m3: '8.00',
  rendimiento_km_l: '10.000', factor_co2_kg_km: '0.30000',
  anio_fabricacion: 2024, estado: 'ACTIVO',
}

const validValues = {
  Placa: ' abc-123 ',
  Tipo: 'CAMIONETA',
  'Capacidad (kg)': '1000.00',
  'Capacidad (m³)': '8.00',
  'Rendimiento (km/L)': '10.000',
  'Factor CO₂ (kg/km)': '0.30000',
  'Año de fabricación': '2024',
}

function change(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } })
}

function fillValid(overrides: Partial<typeof validValues> = {}) {
  for (const [label, value] of Object.entries({ ...validValues, ...overrides })) change(label, value)
}

function submit() {
  fireEvent.submit(screen.getByRole('form', { name: 'Registrar vehículo' }))
}

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (error: Error) => void
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise
    reject = rejectPromise
  })
  return { promise, resolve, reject }
}

async function renderReady(canCreate = true) {
  const result = render(<VehiclesPage canCreate={canCreate} />)
  await waitFor(() => expect(screen.getByRole('button', { name: 'Actualizar listado' })).toBeEnabled())
  return result
}

describe('VehiclesPage', () => {
  beforeEach(() => {
    listMock.mockReset().mockResolvedValue([])
    createMock.mockReset().mockResolvedValue(vehicle)
  })

  it('anuncia carga inicial, marca la región ocupada y luego muestra vacío', async () => {
    const request = deferred<VehicleResponse[]>()
    listMock.mockReturnValueOnce(request.promise)
    render(<VehiclesPage canCreate={false} />)
    expect(screen.getByRole('status')).toHaveTextContent('Cargando vehículos…')
    expect(screen.getByRole('status').closest('[aria-busy="true"]')).toBeNull()
    expect(screen.getByRole('region', { name: 'Listado de vehículos' })).toHaveAttribute('aria-busy', 'true')
    expect(screen.getByRole('button', { name: 'Actualizar listado' })).toBeDisabled()
    await act(async () => { request.resolve([]); await request.promise })
    expect(screen.getByRole('status')).toHaveTextContent('No hay vehículos registrados.')
    expect(screen.getByRole('region', { name: 'Listado de vehículos' })).toHaveAttribute('aria-busy', 'false')
  })

  it('tabla accesible conserva orden, decimales y todos los estados, escapando texto', async () => {
    listMock.mockResolvedValue([
      { ...vehicle, placa: 'ZZZ-123', estado: 'INACTIVO' },
      { ...vehicle, vehiculo_id: '223e4567-e89b-12d3-a456-426614174000' },
      { ...vehicle, vehiculo_id: '323e4567-e89b-12d3-a456-426614174000', placa: 'OTRO', estado: '<script>otro</script>' },
    ])
    await renderReady(false)
    const table = screen.getByRole('table', { name: 'Vehículos registrados, incluidos activos e inactivos' })
    const rows = within(table).getAllByRole('row')
    expect(rows).toHaveLength(4)
    expect(within(rows[1]).getAllByRole('cell')[0]).toHaveTextContent('ZZZ-123')
    expect(within(rows[2]).getAllByRole('cell')[0]).toHaveTextContent('ABC-123')
    expect(within(rows[2]).getAllByRole('cell').map((cell) => cell.textContent)).toEqual([
      'ABC-123', 'Camioneta', '1000.00', '8.00', '10.000', '0.30000', '2024', 'Activo',
    ])
    // Type and state are shown with readable labels; unknown states stay verbatim.
    expect(screen.getByText('Inactivo')).toBeInTheDocument()
    expect(screen.getByText('<script>otro</script>')).toBeInTheDocument()
    expect(table.querySelector('script')).toBeNull()
    for (const header of within(table).getAllByRole('columnheader')) expect(header).toHaveAttribute('scope', 'col')
    expect(screen.getByRole('region', { name: /Tabla de vehículos/u })).toHaveAttribute('tabindex', '0')
  })

  it('GET fallido enfoca la alerta y permite reintentar con teclado sin crear', async () => {
    listMock.mockRejectedValueOnce(new VehicleServiceError('unavailable')).mockResolvedValueOnce([vehicle])
    const user = userEvent.setup()
    await renderReady(false)
    expect(screen.getByRole('alert')).toHaveTextContent('El servicio no está disponible en este momento.')
    await waitFor(() => expect(screen.getByRole('alert')).toHaveFocus())
    const button = screen.getByRole('button', { name: 'Actualizar listado' })
    button.focus()
    await user.keyboard('{Enter}')
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(listMock).toHaveBeenCalledTimes(2)
    expect(createMock).not.toHaveBeenCalled()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('actualización manual anuncia loading y conserva datos con advertencia si falla', async () => {
    listMock.mockResolvedValueOnce([vehicle])
    await renderReady(false)
    const request = deferred<VehicleResponse[]>()
    listMock.mockReturnValueOnce(request.promise)
    fireEvent.click(screen.getByRole('button', { name: 'Actualizar listado' }))
    expect(screen.getByRole('status')).toHaveTextContent('Cargando vehículos…')
    expect(screen.getByRole('table')).toBeInTheDocument()
    await act(async () => { request.reject(new Error('private detail')); await request.promise.catch(() => undefined) })
    expect(screen.getByRole('alert')).toHaveTextContent('No se pudo completar la operación.')
    expect(screen.getByRole('alert')).toHaveTextContent('El listado mostrado puede estar desactualizado.')
    expect(screen.queryByText('private detail')).not.toBeInTheDocument()
    expect(createMock).not.toHaveBeenCalled()
  })

  it('monta exactamente siete controles requeridos y catálogo accesible', async () => {
    await renderReady()
    const form = screen.getByRole('form', { name: 'Registrar vehículo' })
    expect(form).toHaveAttribute('aria-busy', 'false')
    expect(form).toHaveAccessibleDescription(/Todos los campos son obligatorios/u)
    expect(form.querySelectorAll('input, select')).toHaveLength(7)
    for (const label of Object.keys(validValues)) {
      const input = screen.getByLabelText(label)
      expect(input).toBeRequired()
      expect(input).toHaveAttribute('aria-invalid', 'false')
    }
    for (const label of ['Capacidad (kg)', 'Capacidad (m³)', 'Rendimiento (km/L)', 'Factor CO₂ (kg/km)']) {
      expect(screen.getByLabelText(label)).toHaveAttribute('type', 'text')
      expect(screen.getByLabelText(label)).toHaveAttribute('inputmode', 'decimal')
    }
    expect(screen.getByLabelText('Año de fabricación')).toHaveAttribute('inputmode', 'numeric')
    expect(screen.getAllByRole('option').map((option) => option.getAttribute('value'))).toEqual(['', 'CAMIONETA', 'FURGON', 'MOTO'])
    expect(screen.queryByLabelText('Estado')).not.toBeInTheDocument()
  })

  it('valida campos vacíos, asocia descripción y enfoca el primero', async () => {
    await renderReady()
    submit()
    const plate = screen.getByLabelText('Placa')
    expect(plate).toHaveFocus()
    expect(plate).toHaveAttribute('aria-invalid', 'true')
    // Error first, then the persistent help text under the field.
    expect(plate).toHaveAccessibleDescription(/^La placa es obligatoria\. /u)
    expect(screen.getByRole('alert')).toHaveTextContent('Revisa los campos indicados')
    for (const label of Object.keys(validValues)) expect(screen.getByLabelText(label)).toHaveAttribute('aria-invalid', 'true')
    expect(createMock).not.toHaveBeenCalled()
  })

  it.each([
    ['Placa', '   '], ['Placa', 'ABCDEFGHIJK'], ['Placa', 'ß'.repeat(6)],
    ['Tipo', ''], ['Tipo', 'AUTO'],
    ['Capacidad (kg)', '0'], ['Capacidad (m³)', '-1'],
    ['Rendimiento (km/L)', '0.0000'], ['Factor CO₂ (kg/km)', '-0.00001'],
    ['Capacidad (kg)', 'NaN'], ['Capacidad (m³)', 'Infinity'],
    ['Capacidad (kg)', '1e3'], ['Capacidad (kg)', '1,25'], ['Capacidad (kg)', ' 1.25 '],
    ['Capacidad (kg)', '100000000'], ['Capacidad (m³)', '100000000.00'],
    ['Rendimiento (km/L)', '10000000'], ['Factor CO₂ (kg/km)', '100000'],
    ['Capacidad (kg)', '1.001'], ['Capacidad (m³)', '0.00010'],
    ['Rendimiento (km/L)', '1.0001'], ['Factor CO₂ (kg/km)', '1.000001'],
    ['Año de fabricación', '1979'], ['Año de fabricación', '2101'],
    ['Año de fabricación', '2024.5'], ['Año de fabricación', '2e3'],
  ])('rechaza %s=%s, conserva valor y enfoca el campo', async (label, value) => {
    await renderReady()
    fillValid({ [label]: value })
    submit()
    const control = screen.getByLabelText(label)
    expect(control).toHaveAttribute('aria-invalid', 'true')
    expect(control).toHaveFocus()
    if (label !== 'Tipo') expect(control).toHaveValue(value)
    expect(createMock).not.toHaveBeenCalled()
  })

  it.each(['CAMIONETA', 'FURGON', 'MOTO'] as const)('envía tipo %s, placa original y cuatro strings decimales', async (tipo) => {
    await renderReady()
    fillValid({ Tipo: tipo })
    submit()
    await screen.findByText('Vehículo registrado: ABC-123.')
    expect(createMock).toHaveBeenCalledExactlyOnceWith({
      placa: ' abc-123 ', tipo,
      capacidad_kg: '1000.00', capacidad_m3: '8.00',
      rendimiento_km_l: '10.000', factor_co2_kg_km: '0.30000',
      anio_fabricacion: 2024,
    })
  })

  it.each(['1980', '2100'])('acepta máximos decimales, año %s y longitud de placa después de normalizar', async (year) => {
    await renderReady()
    fillValid({
      Placa: ' abcdefghij ', 'Capacidad (kg)': '99999999.99', 'Capacidad (m³)': '99999999.99',
      'Rendimiento (km/L)': '9999999.999', 'Factor CO₂ (kg/km)': '99999.99999', 'Año de fabricación': year,
    })
    submit()
    await screen.findByText('Vehículo registrado: ABC-123.')
    expect(createMock).toHaveBeenCalledWith(expect.objectContaining({ placa: ' abcdefghij ', anio_fabricacion: Number(year) }))
  })

  it('acepta ceros finales e iniciales, precisión mínima y factor CO₂ cero sin alterar strings', async () => {
    await renderReady()
    fillValid({
      'Capacidad (kg)': '00001.2300', 'Capacidad (m³)': '0.01000',
      'Rendimiento (km/L)': '0.00100', 'Factor CO₂ (kg/km)': '0.0000000',
    })
    submit()
    await screen.findByText('Vehículo registrado: ABC-123.')
    expect(createMock).toHaveBeenCalledWith(expect.objectContaining({
      capacidad_kg: '00001.2300', capacidad_m3: '0.01000',
      rendimiento_km_l: '0.00100', factor_co2_kg_km: '0.0000000',
    }))
  })

  it('limpia error visual al corregir y mantiene la placa como fue escrita', async () => {
    await renderReady()
    fillValid({ Placa: '' })
    submit()
    const user = userEvent.setup()
    await user.type(screen.getByLabelText('Placa'), ' ab-c ')
    expect(screen.getByLabelText('Placa')).toHaveValue(' ab-c ')
    expect(screen.getByLabelText('Placa')).toHaveAttribute('aria-invalid', 'false')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('impide doble submit, anuncia envío y bloquea controles hasta completar', async () => {
    const request = deferred<VehicleResponse>()
    createMock.mockReturnValueOnce(request.promise)
    await renderReady()
    fillValid()
    submit()
    submit()
    expect(createMock).toHaveBeenCalledTimes(1)
    expect(screen.getByText('Registrando vehículo…')).toHaveAttribute('role', 'status')
    expect(screen.getByText('Registrando vehículo…').closest('[aria-busy="true"]')).toBeNull()
    expect(screen.getByRole('form')).toHaveAttribute('aria-busy', 'true')
    expect(screen.getByRole('button', { name: 'Registrando…' })).toBeDisabled()
    expect(screen.getByLabelText('Placa')).toBeDisabled()
    await act(async () => { request.resolve(vehicle); await request.promise })
    expect(screen.getByRole('button', { name: 'Registrar vehículo' })).toBeEnabled()
  })

  it('alta exitosa anuncia placa canónica, limpia campos y errores, y actualiza listado', async () => {
    listMock.mockResolvedValueOnce([]).mockResolvedValueOnce([vehicle])
    await renderReady()
    submit()
    fillValid()
    submit()
    expect((await screen.findByText('Vehículo registrado: ABC-123.')).closest('[role="status"]')).not.toBeNull()
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(listMock).toHaveBeenCalledTimes(2)
    expect(createMock).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    for (const label of Object.keys(validValues)) {
      expect(screen.getByLabelText(label)).toHaveValue('')
      expect(screen.getByLabelText(label)).toHaveAttribute('aria-invalid', 'false')
    }
  })

  it('refresh fallido conserva el éxito y reintenta solo GET', async () => {
    listMock.mockResolvedValueOnce([])
      .mockRejectedValueOnce(new VehicleServiceError('network'))
      .mockResolvedValueOnce([vehicle])
    await renderReady()
    fillValid()
    submit()
    expect(await screen.findByRole('alert')).toHaveTextContent('Vehículo registrado. No se pudo actualizar el listado.')
    expect(screen.getByText('Vehículo registrado: ABC-123.')).toBeInTheDocument()
    expect(screen.getByLabelText('Placa')).toHaveValue('')
    fireEvent.click(screen.getByRole('button', { name: 'Actualizar listado' }))
    await screen.findByRole('table')
    expect(listMock).toHaveBeenCalledTimes(3)
    expect(createMock).toHaveBeenCalledTimes(1)
  })

  it.each(['resolve', 'reject'] as const)('GET antiguo (%s) no sobrescribe refresh después de crear', async (settlement) => {
    const oldRequest = deferred<VehicleResponse[]>()
    listMock.mockReturnValueOnce(oldRequest.promise).mockResolvedValueOnce([vehicle])
    render(<VehiclesPage canCreate />)
    fillValid()
    submit()
    await screen.findByRole('table')
    await act(async () => {
      if (settlement === 'resolve') oldRequest.resolve([{ ...vehicle, placa: 'OLD-123' }])
      else oldRequest.reject(new VehicleServiceError('unavailable'))
      await oldRequest.promise.catch(() => undefined)
    })
    expect(within(screen.getByRole('table')).getByText('ABC-123')).toBeInTheDocument()
    expect(screen.queryByText('OLD-123')).not.toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('StrictMode invalida el GET del primer montaje', async () => {
    const oldRequest = deferred<VehicleResponse[]>()
    listMock.mockReturnValueOnce(oldRequest.promise).mockResolvedValueOnce([vehicle])
    render(<StrictMode><VehiclesPage canCreate={false} /></StrictMode>)
    await screen.findByRole('table')
    await act(async () => { oldRequest.resolve([]); await oldRequest.promise })
    expect(screen.getByRole('table')).toBeInTheDocument()
    expect(screen.queryByText('No hay vehículos registrados.')).not.toBeInTheDocument()
  })

  it('409 conserva los siete valores y enfoca placa', async () => {
    createMock.mockRejectedValueOnce(new VehicleServiceError('conflict', { status: 409 }))
    await renderReady()
    fillValid()
    submit()
    expect(await screen.findByRole('alert')).toHaveTextContent('La placa ya está registrada.')
    await waitFor(() => expect(screen.getByLabelText('Placa')).toHaveFocus())
    expect(screen.getByLabelText('Placa')).toHaveAccessibleDescription(/^La placa ya está registrada\. /u)
    for (const [label, value] of Object.entries(validValues)) expect(screen.getByLabelText(label)).toHaveValue(value)
    expect(listMock).toHaveBeenCalledTimes(1)
  })

  it('422 asocia campos y enfoca el primero en orden de formulario', async () => {
    createMock.mockRejectedValueOnce(new VehicleServiceError('validation', {
      status: 422, issues: [
        { field: 'anio_fabricacion', message: 'Revisa el año de fabricación.' },
        { field: 'capacidad_m3', message: 'Revisa la capacidad en m³.' },
      ],
    }))
    await renderReady()
    fillValid()
    submit()
    expect(await screen.findByRole('alert')).toHaveTextContent('Revisa los datos ingresados.')
    // The redesigned form groups Año de fabricación with identification, before capacities.
    await waitFor(() => expect(screen.getByLabelText('Año de fabricación')).toHaveFocus())
    expect(screen.getByLabelText('Capacidad (m³)')).toHaveAccessibleDescription(/^Revisa la capacidad en m³\. /u)
    expect(screen.getByLabelText('Año de fabricación')).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByLabelText('Placa')).toHaveValue(validValues.Placa)
  })

  it.each([
    new VehicleServiceError('unauthorized'), new VehicleServiceError('forbidden'),
    new VehicleServiceError('unavailable'), new VehicleServiceError('network'),
    new VehicleServiceError('validation'), new VehicleServiceError('unexpected'),
    new Error('private detail'),
  ])('errores generales conservan formulario y enfocan alerta: %s', async (error) => {
    createMock.mockRejectedValueOnce(error)
    await renderReady()
    fillValid()
    submit()
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(error instanceof VehicleServiceError ? error.message : 'No se pudo completar la operación.')
    await waitFor(() => expect(alert).toHaveFocus())
    expect(screen.getByLabelText('Placa')).toHaveValue(validValues.Placa)
    expect(screen.getByRole('button', { name: 'Registrar vehículo' })).toBeEnabled()
    expect(screen.queryByText('private detail')).not.toBeInTheDocument()
    expect(listMock).toHaveBeenCalledTimes(1)
  })

  it('modo auditor no monta formulario ni acciones de creación', async () => {
    await renderReady(false)
    expect(screen.queryByRole('form')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Registrar vehículo' })).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Placa')).not.toBeInTheDocument()
    expect(createMock).not.toHaveBeenCalled()
  })

  it.each(['resolve', 'reject'] as const)('ignora GET pendiente tras desmontar: %s', async (settlement) => {
    const request = deferred<VehicleResponse[]>()
    listMock.mockReturnValueOnce(request.promise)
    const view = render(<VehiclesPage canCreate={false} />)
    view.unmount()
    await act(async () => {
      if (settlement === 'resolve') request.resolve([vehicle])
      else request.reject(new Error('private'))
      await request.promise.catch(() => undefined)
    })
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it.each(['resolve', 'reject'] as const)('ignora POST pendiente tras desmontar sin disparar refresh: %s', async (settlement) => {
    const request = deferred<VehicleResponse>()
    createMock.mockReturnValueOnce(request.promise)
    const view = await renderReady()
    fillValid()
    submit()
    view.unmount()
    await act(async () => {
      if (settlement === 'resolve') request.resolve(vehicle)
      else request.reject(new VehicleServiceError('network'))
      await request.promise.catch(() => undefined)
    })
    expect(listMock).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})
