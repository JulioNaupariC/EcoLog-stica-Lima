import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {
  createOrder,
  OrderCreateResponse,
  OrderServiceError,
} from '../services/orders'
import { searchClients } from '../services/clients'
import { getDeliveryPreferences, PreferencesServiceError } from '../services/deliveryPreferences'
import { OrderCreatePage } from './OrderCreatePage'

vi.mock('../services/orders', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../services/orders')>()
  return { ...actual, createOrder: vi.fn() }
})
vi.mock('../services/clients', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../services/clients')>()
  return { ...actual, searchClients: vi.fn() }
})
vi.mock('../services/deliveryPreferences', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../services/deliveryPreferences')>()
  return { ...actual, getDeliveryPreferences: vi.fn() }
})

const createOrderMock = vi.mocked(createOrder)
const searchClientsMock = vi.mocked(searchClients)
const getPreferencesMock = vi.mocked(getDeliveryPreferences)

const CLIENT = { cliente_id: '123e4567-e89b-12d3-a456-426614174000', nombre: 'Bodega Ficticia Norte' }
const OTHER_CLIENT = { cliente_id: '323e4567-e89b-12d3-a456-426614174000', nombre: 'Farmacia Ejemplo Centro' }
const PREFERENCES = {
  cliente_id: CLIENT.cliente_id,
  horario_preferido: 'Mañana (preferido)',
  referencia: 'Puerta junto al parque',
  restriccion_acceso: 'Ingreso por puerta lateral',
}

const createdOrder: OrderCreateResponse = {
  pedido_id: '223e4567-e89b-12d3-a456-426614174000',
  estado: 'PENDIENTE',
  cliente_id: '123e4567-e89b-12d3-a456-426614174000',
  direccion: 'Av. Principal 123',
  referencia: 'Frente al parque',
  latitud: -11.987654,
  longitud: -76.987654,
  peso_kg: '12.50',
  volumen_m3: '0.080',
  ventana_inicio: '2026-10-01T14:00:00.000Z',
  ventana_fin: '2026-10-01T16:00:00.000Z',
  prioridad: 'ESTANDAR',
  tipo_producto: 'Libre',
}

const validValues = {
  Dirección: ' Av. Principal 123 ',
  'Punto de referencia': ' Frente al parque ',
  Latitud: '-11.987654',
  Longitud: '-76.987654',
  'Peso (kg)': '12.50',
  'Volumen (m³)': '0.080',
  'Inicio de ventana': '2026-10-01T09:00',
  'Fin de ventana': '2026-10-01T11:00',
  'Tipo de producto': ' Libre ',
}

function change(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } })
}

function clientInput() {
  return screen.getByRole('combobox', { name: 'Cliente' })
}

async function selectClient(name = CLIENT.nombre) {
  fireEvent.change(clientInput(), { target: { value: name.slice(0, 6) } })
  fireEvent.click(await screen.findByRole('option', { name: new RegExp(name, 'u') }))
}

async function fillValid(overrides: Partial<typeof validValues> = {}, { withClient = true } = {}) {
  if (withClient) await selectClient()
  for (const [label, value] of Object.entries({ ...validValues, ...overrides })) {
    change(label, value)
  }
}

function submit() {
  fireEvent.submit(screen.getByRole('button', { name: 'Registrar pedido' }).closest('form')!)
}

describe('OrderCreatePage', () => {
  beforeEach(() => {
    createOrderMock.mockReset()
    createOrderMock.mockResolvedValue(createdOrder)
    searchClientsMock.mockReset()
    searchClientsMock.mockImplementation((term) => {
      const items = [CLIENT, OTHER_CLIENT].filter(item => item.nombre.toLowerCase().includes(term.trim().toLowerCase()))
      return Promise.resolve({ items, page: 1, page_size: 8, total: items.length })
    })
    getPreferencesMock.mockReset()
    getPreferencesMock.mockImplementation((id) => Promise.resolve(
      id === CLIENT.cliente_id
        ? PREFERENCES
        : { cliente_id: id, horario_preferido: null, referencia: null, restriccion_acceso: null },
    ))
  })

  it('renderiza todos los controles con etiquetas accesibles', () => {
    render(<OrderCreatePage />)

    expect(clientInput()).toHaveAttribute('aria-expanded', 'false')
    for (const label of Object.keys(validValues)) {
      expect(screen.getByLabelText(label)).toBeInTheDocument()
    }
    expect(screen.getByLabelText('Prioridad')).toHaveValue('ESTANDAR')
    expect(screen.getByRole('button', { name: 'Registrar pedido' })).toBeEnabled()
  })

  it.each([
    ['sin texto', ''],
    ['texto sin seleccionar una opción', '123e4567-e89b-12d3-a456-426614174000'],
  ])('ruta infeliz: exige seleccionar un cliente (%s)', async (_case, typed) => {
    render(<OrderCreatePage />)
    await fillValid({}, { withClient: false })
    if (typed) fireEvent.change(clientInput(), { target: { value: typed } })
    submit()

    expect(screen.getByText('Selecciona un cliente de la lista.')).toBeInTheDocument()
    expect(clientInput()).toHaveAttribute('aria-invalid', 'true')
    expect(createOrderMock).not.toHaveBeenCalled()
  })

  it('valida dirección vacía', async () => {
    render(<OrderCreatePage />)
    await fillValid({ Dirección: '   ' })
    submit()

    expect(screen.getByText('La dirección es obligatoria.')).toBeInTheDocument()
  })

  it('exige referencia o coordenadas completas', async () => {
    render(<OrderCreatePage />)
    await fillValid({ 'Punto de referencia': '', Latitud: '', Longitud: '' })
    submit()

    expect(screen.getByText('Ingresa coordenadas completas o un punto de referencia.')).toBeInTheDocument()
    expect(createOrderMock).not.toHaveBeenCalled()
  })

  it('rechaza una sola coordenada', async () => {
    render(<OrderCreatePage />)
    await fillValid({ 'Punto de referencia': '', Longitud: '' })
    submit()

    expect(screen.getAllByText('Latitud y longitud deben ingresarse juntas.')).toHaveLength(2)
  })

  it.each([
    ['Latitud', '91', 'La latitud debe estar entre -90 y 90.'],
    ['Longitud', '-181', 'La longitud debe estar entre -180 y 180.'],
  ])('rechaza %s fuera de rango', async (label, value, message) => {
    render(<OrderCreatePage />)
    await fillValid({ [label]: value })
    submit()

    expect(screen.getByText(message)).toBeInTheDocument()
  })

  it.each([
    ['Peso (kg)', '0', 'El peso debe ser mayor que cero y tener como máximo 2 decimales.'],
    ['Peso (kg)', '1.001', 'El peso debe ser mayor que cero y tener como máximo 2 decimales.'],
    ['Volumen (m³)', '-1', 'El volumen debe ser mayor que cero y tener como máximo 3 decimales.'],
    ['Volumen (m³)', '1.0001', 'El volumen debe ser mayor que cero y tener como máximo 3 decimales.'],
  ])('valida decimales de %s con valor %s', async (label, value, message) => {
    render(<OrderCreatePage />)
    await fillValid({ [label]: value })
    submit()

    expect(screen.getByText(message)).toBeInTheDocument()
  })

  it.each([
    ['', 'El tipo de producto es obligatorio.'],
    ['x'.repeat(21), 'El tipo de producto no puede superar 20 caracteres.'],
  ])('valida tipo_producto', async (value, message) => {
    render(<OrderCreatePage />)
    await fillValid({ 'Tipo de producto': value })
    submit()

    expect(screen.getByText(message)).toBeInTheDocument()
  })

  it('rechaza una ventana final igual o anterior al inicio', async () => {
    render(<OrderCreatePage />)
    await fillValid({ 'Fin de ventana': '2026-10-01T09:00' })
    submit()

    expect(screen.getByText('La hora final debe ser posterior a la hora inicial.')).toBeInTheDocument()
  })

  it('envía prioridad, strings decimales y fechas ISO timezone-aware', async () => {
    render(<OrderCreatePage />)
    await fillValid()
    fireEvent.change(screen.getByLabelText('Prioridad'), { target: { value: 'EXPRESS' } })
    submit()

    await waitFor(() => expect(createOrderMock).toHaveBeenCalledTimes(1))
    expect(createOrderMock).toHaveBeenCalledWith({
      cliente_id: '123e4567-e89b-12d3-a456-426614174000',
      direccion: 'Av. Principal 123',
      referencia: 'Frente al parque',
      latitud: -11.987654,
      longitud: -76.987654,
      peso_kg: '12.50',
      volumen_m3: '0.080',
      ventana_inicio: new Date('2026-10-01T09:00').toISOString(),
      ventana_fin: new Date('2026-10-01T11:00').toISOString(),
      prioridad: 'EXPRESS',
      tipo_producto: 'Libre',
    })
  })

  it('envía null para referencia y coordenadas vacías cuando la otra ubicación existe', async () => {
    render(<OrderCreatePage />)
    await fillValid({ Latitud: '', Longitud: '' })
    submit()
    await waitFor(() => expect(createOrderMock).toHaveBeenCalledTimes(1))
    expect(createOrderMock.mock.calls[0]?.[0]).toMatchObject({ latitud: null, longitud: null })

    createOrderMock.mockClear()
    change('Punto de referencia', '')
    change('Latitud', '-11.9')
    change('Longitud', '-76.9')
    submit()
    await waitFor(() => expect(createOrderMock).toHaveBeenCalledTimes(1))
    expect(createOrderMock.mock.calls[0]?.[0]).toMatchObject({ referencia: null })
  })

  it('deshabilita el botón durante loading e impide doble submit', async () => {
    let resolveRequest!: (order: OrderCreateResponse) => void
    createOrderMock.mockImplementation(() => new Promise((resolve) => { resolveRequest = resolve }))
    render(<OrderCreatePage />)
    await fillValid()

    const form = screen.getByRole('button', { name: 'Registrar pedido' }).closest('form')!
    fireEvent.submit(form)
    fireEvent.submit(form)

    expect(screen.getByRole('button', { name: 'Registrando…' })).toBeDisabled()
    expect(createOrderMock).toHaveBeenCalledTimes(1)
    act(() => resolveRequest(createdOrder))
    await waitFor(() => expect(screen.getByRole('status')).toBeInTheDocument())
  })

  it('muestra pedido_id y estado después del éxito', async () => {
    render(<OrderCreatePage />)
    await fillValid()
    submit()

    expect(await screen.findByRole('status')).toHaveTextContent('Pedido registrado.')
    expect(screen.getByRole('status')).toHaveTextContent(createdOrder.pedido_id)
    expect(screen.getByRole('status')).toHaveTextContent('PENDIENTE')
  })

  it.each([
    ['unauthorized', 'Tu sesión no está disponible o ha vencido.'],
    ['forbidden', 'No tienes permisos para registrar pedidos.'],
    ['client-not-found', 'El cliente indicado no existe.'],
    ['unavailable', 'El servicio no está disponible en este momento.'],
    ['network', 'No se pudo conectar con el servicio.'],
  ] as const)('muestra el error de servicio %s y conserva el formulario', async (kind, message) => {
    createOrderMock.mockRejectedValue(new OrderServiceError(kind, message))
    render(<OrderCreatePage />)
    await fillValid()
    submit()

    expect(await screen.findByRole('alert')).toHaveTextContent(message)
    expect(screen.getByLabelText('Dirección')).toHaveValue(' Av. Principal 123 ')
    expect(screen.getByRole('button', { name: 'Registrar pedido' })).toBeEnabled()
  })

  it('mapea el 422 a campo y conserva errores de modelo en el resumen', async () => {
    createOrderMock.mockRejectedValue(new OrderServiceError(
      'validation',
      'Revisa los datos ingresados.',
      {
        status: 422,
        issues: [
          { field: 'peso_kg', message: 'El peso no es válido' },
          { message: 'La ubicación no cumple la regla combinada' },
        ],
      },
    ))
    render(<OrderCreatePage />)
    await fillValid()
    submit()

    expect(await screen.findByRole('alert')).toHaveTextContent('Revisa los datos ingresados.')
    expect(screen.getByRole('alert')).toHaveTextContent('La ubicación no cumple la regla combinada')
    expect(screen.getByText('El peso no es válido')).toBeInTheDocument()
    expect(screen.queryByText('[object Object]')).not.toBeInTheDocument()
  })

  it('limpia el error del campo cuando el usuario lo corrige', async () => {
    const user = userEvent.setup()
    render(<OrderCreatePage />)
    await fillValid({}, { withClient: false })
    submit()
    const input = clientInput()
    expect(input).toHaveAttribute('aria-invalid', 'true')

    await user.type(input, 'Bodega')
    await user.click(await screen.findByRole('option', { name: /Bodega Ficticia Norte/u }))
    expect(input).toHaveAttribute('aria-invalid', 'false')
  })

  it('presenta un error seguro ante un rechazo no tipado', async () => {
    createOrderMock.mockRejectedValue(new Error('detalle interno'))
    render(<OrderCreatePage />)
    await fillValid()
    submit()

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo registrar el pedido.')
    expect(screen.queryByText('detalle interno')).not.toBeInTheDocument()
  })
})

describe('OrderCreatePage — P8 / D-01: propuesta de preferencias del cliente', () => {
  beforeEach(() => {
    createOrderMock.mockReset()
    createOrderMock.mockResolvedValue(createdOrder)
    searchClientsMock.mockReset()
    searchClientsMock.mockImplementation((term) => {
      const items = [CLIENT, OTHER_CLIENT].filter(item => item.nombre.toLowerCase().includes(term.trim().toLowerCase()))
      return Promise.resolve({ items, page: 1, page_size: 8, total: items.length })
    })
    getPreferencesMock.mockReset()
    getPreferencesMock.mockImplementation((id) => Promise.resolve(
      id === CLIENT.cliente_id
        ? PREFERENCES
        : { cliente_id: id, horario_preferido: null, referencia: null, restriccion_acceso: null },
    ))
  })

  it('ruta dorada: propone las preferencias y copia la referencia solo con la acción explícita', async () => {
    render(<OrderCreatePage />)
    await fillValid({ 'Punto de referencia': 'Referencia propia del pedido' })

    const panel = await screen.findByRole('region', { name: 'Preferencias del cliente' })
    expect(await within(panel).findByText('Mañana (preferido)')).toBeInTheDocument()
    expect(within(panel).getByText('Ingreso por puerta lateral')).toBeInTheDocument()
    expect(getPreferencesMock).toHaveBeenCalledWith(CLIENT.cliente_id)

    fireEvent.click(within(panel).getByRole('button', { name: 'Usar como referencia del pedido' }))
    expect(screen.getByLabelText('Punto de referencia')).toHaveValue('Puerta junto al parque')
    expect(within(panel).getByText('Referencia copiada al pedido. Puedes editarla antes de registrar.')).toBeInTheDocument()

    submit()
    await waitFor(() => expect(createOrderMock).toHaveBeenCalledTimes(1))
    expect(createOrderMock.mock.calls[0]?.[0]).toMatchObject({
      cliente_id: CLIENT.cliente_id,
      referencia: 'Puerta junto al parque',
      ventana_inicio: new Date('2026-10-01T09:00').toISOString(),
      ventana_fin: new Date('2026-10-01T11:00').toISOString(),
    })
  })

  it('ruta feliz: sin la acción, no copia horario, restricción ni referencia al pedido (RN-006)', async () => {
    render(<OrderCreatePage />)
    await fillValid({ 'Punto de referencia': 'Referencia propia del pedido' })
    await screen.findByText('Mañana (preferido)')

    expect(screen.getByLabelText('Punto de referencia')).toHaveValue('Referencia propia del pedido')
    expect(screen.getByLabelText('Inicio de ventana')).toHaveValue('2026-10-01T09:00')
    expect(screen.getByLabelText('Fin de ventana')).toHaveValue('2026-10-01T11:00')
    submit()
    await waitFor(() => expect(createOrderMock).toHaveBeenCalledTimes(1))
    const payload = createOrderMock.mock.calls[0]?.[0]
    expect(payload?.referencia).toBe('Referencia propia del pedido')
    expect(JSON.stringify(payload)).not.toContain('Mañana')
    expect(JSON.stringify(payload)).not.toContain('puerta lateral')
  })

  it.each([
    ['forbidden', 'No tienes permisos para ver las preferencias de este cliente.'],
    ['unavailable', 'No se pudieron cargar las preferencias del cliente. Puedes registrar el pedido igualmente.'],
    ['not_found', 'No se pudieron cargar las preferencias del cliente. Puedes registrar el pedido igualmente.'],
  ] as const)('ruta infeliz: si las preferencias fallan (%s) el pedido sigue registrable', async (kind, message) => {
    getPreferencesMock.mockRejectedValue(new PreferencesServiceError(kind))
    render(<OrderCreatePage />)
    await fillValid()

    expect(await screen.findByText(message)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Usar como referencia del pedido' })).not.toBeInTheDocument()
    submit()
    await waitFor(() => expect(createOrderMock).toHaveBeenCalledTimes(1))
  })

  it('ruta infeliz: un cliente inexistente en el registro muestra el error del servicio', async () => {
    createOrderMock.mockRejectedValue(new OrderServiceError('client-not-found', 'El cliente indicado no existe.'))
    render(<OrderCreatePage />)
    await fillValid()
    submit()

    expect(await screen.findByRole('alert')).toHaveTextContent('El cliente indicado no existe.')
  })

  it('ruta de borde: cliente sin preferencias y cambio de cliente recargan el panel', async () => {
    render(<OrderCreatePage />)
    await fillValid()
    await screen.findByText('Mañana (preferido)')

    await selectClient(OTHER_CLIENT.nombre)
    await waitFor(() => expect(getPreferencesMock).toHaveBeenLastCalledWith(OTHER_CLIENT.cliente_id))
    const panel = screen.getByRole('region', { name: 'Preferencias del cliente' })
    await waitFor(() => expect(within(panel).getAllByText('Sin registrar')).toHaveLength(3))
    expect(within(panel).queryByRole('button', { name: 'Usar como referencia del pedido' })).not.toBeInTheDocument()
    expect(screen.queryByText('Mañana (preferido)')).not.toBeInTheDocument()
  })

  it('ruta de borde: la acción se deshabilita si la referencia del pedido ya coincide', async () => {
    render(<OrderCreatePage />)
    await fillValid({ 'Punto de referencia': 'Puerta junto al parque' })

    expect(await screen.findByRole('button', { name: 'Usar como referencia del pedido' })).toBeDisabled()
  })
})
