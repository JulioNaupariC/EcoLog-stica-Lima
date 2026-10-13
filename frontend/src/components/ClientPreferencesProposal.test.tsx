import { act, fireEvent, render, screen } from '@testing-library/react'
import { ClientPreferencesProposal } from './ClientPreferencesProposal'
import type { DeliveryPreferences } from '../services/deliveryPreferences'

const id = '123e4567-e89b-12d3-a456-426614174000'
const full: DeliveryPreferences = {
  cliente_id: id, horario_preferido: 'Mañana (preferido)',
  referencia: 'Puerta junto al parque', restriccion_acceso: 'Ingreso por puerta lateral',
}

describe('ClientPreferencesProposal', () => {
  it('ruta dorada: muestra contexto y copia la referencia con la acción explícita', async () => {
    const onUse = vi.fn()
    render(<ClientPreferencesProposal clientId={id} orderReference="" onUseReference={onUse} load={() => Promise.resolve(full)} />)
    expect(screen.getByText('Cargando preferencias del cliente…')).toBeInTheDocument()
    fireEvent.click(await screen.findByRole('button', { name: 'Usar como referencia del pedido' }))
    expect(onUse).toHaveBeenCalledWith('Puerta junto al parque')
    expect(screen.getByText('Solo informativo: la ventana del pedido se define en sus propios campos.')).toBeInTheDocument()
  })

  it('ruta de borde: ignora la respuesta si el componente se desmonta antes', async () => {
    let resolve!: (value: DeliveryPreferences) => void
    const view = render(<ClientPreferencesProposal clientId={id} orderReference="" onUseReference={vi.fn()}
      load={() => new Promise(done => { resolve = done })} />)
    view.unmount()
    await act(() => { resolve(full); return Promise.resolve() })
    expect(screen.queryByText('Mañana (preferido)')).not.toBeInTheDocument()
  })

  it('ruta de borde: texto en blanco cuenta como sin registrar y no ofrece copia', async () => {
    render(<ClientPreferencesProposal clientId={id} orderReference="" onUseReference={vi.fn()}
      load={() => Promise.resolve({ ...full, referencia: '   ', horario_preferido: null })} />)
    expect(await screen.findAllByText('Sin registrar')).toHaveLength(2)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})
