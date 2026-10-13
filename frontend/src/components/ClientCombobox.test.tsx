import { useState } from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ClientCombobox } from './ClientCombobox'
import { ClientsServiceError } from '../services/clients'
import type { ClientOption, ClientPage } from '../services/clients'

const CLIENTS: ClientOption[] = [
  { cliente_id: '11111111-e89b-12d3-a456-426614174000', nombre: 'Bodega Ficticia Norte' },
  { cliente_id: '22222222-e89b-12d3-a456-426614174000', nombre: 'Bodega Ficticia Sur' },
  { cliente_id: '33333333-e89b-12d3-a456-426614174000', nombre: 'Bodega Ficticia Sur' },
]

function pageOf(items: ClientOption[], total = items.length): ClientPage {
  return { items, page: 1, page_size: 8, total }
}

function Harness({ search, onAccessError }: {
  search: (term: string, options: { signal?: AbortSignal }) => Promise<ClientPage>
  onAccessError?: (error: ClientsServiceError) => void
}) {
  const [selected, setSelected] = useState<ClientOption | null>(null)
  return <form aria-label="Prueba" onSubmit={event => event.preventDefault()}>
    <ClientCombobox id="cliente" label="Cliente" hint="Busca por nombre." selected={selected}
      onSelect={setSelected} debounceMs={0} search={search} onAccessError={onAccessError} />
    <output data-testid="selected">{selected?.cliente_id ?? 'ninguno'}</output>
  </form>
}

function combobox() { return screen.getByRole('combobox', { name: 'Cliente' }) }

describe('ClientCombobox', () => {
  it('ruta dorada: teclado completo — escribir, flechas, Enter selecciona sin enviar el formulario', async () => {
    const user = userEvent.setup()
    const search = vi.fn((term: string) => Promise.resolve(pageOf(CLIENTS.filter(item => item.nombre.toLowerCase().includes(term.toLowerCase())))))
    const submitted = vi.fn()
    render(<Harness search={search} />)
    screen.getByRole('form').addEventListener('submit', submitted)

    await user.type(combobox(), 'bodega')
    const list = await screen.findByRole('listbox')
    expect(combobox()).toHaveAttribute('aria-expanded', 'true')
    expect(combobox()).toHaveAttribute('aria-controls', list.id)
    expect(combobox()).toHaveAttribute('aria-autocomplete', 'list')
    await waitFor(() => expect(screen.getAllByRole('option')).toHaveLength(3))
    expect(combobox()).toHaveAttribute('aria-activedescendant', screen.getAllByRole('option')[0].id)

    await user.keyboard('{ArrowDown}')
    expect(screen.getAllByRole('option')[1]).toHaveAttribute('aria-selected', 'true')
    expect(combobox()).toHaveAttribute('aria-activedescendant', screen.getAllByRole('option')[1].id)
    await user.keyboard('{Enter}')

    expect(screen.getByTestId('selected')).toHaveTextContent(CLIENTS[1].cliente_id)
    expect(combobox()).toHaveValue('Bodega Ficticia Sur')
    expect(combobox()).toHaveAttribute('aria-expanded', 'false')
    expect(screen.getByText(/Cliente seleccionado:/u)).toHaveTextContent('ID 22222222')
    expect(submitted).not.toHaveBeenCalled()
  })

  it('ruta feliz: clic en una opción, homónimos distinguibles por ID y anuncio del resultado', async () => {
    const search = vi.fn(() => Promise.resolve(pageOf(CLIENTS.slice(1), 5)))
    render(<Harness search={search} />)
    fireEvent.change(combobox(), { target: { value: 'Sur' } })

    expect(await screen.findByText('2 clientes de 5. Escribe más para acotar.')).toHaveAttribute('aria-live', 'polite')
    const options = screen.getAllByRole('option', { name: /Bodega Ficticia Sur/u })
    expect(options[0]).toHaveTextContent('ID 22222222')
    expect(options[1]).toHaveTextContent('ID 33333333')
    fireEvent.click(options[1])
    expect(screen.getByTestId('selected')).toHaveTextContent(CLIENTS[2].cliente_id)
  })

  it.each([
    [new ClientsServiceError('forbidden'), 'No tienes permisos para consultar clientes.', true],
    [new ClientsServiceError('unavailable'), 'El servicio no está disponible. Intenta nuevamente más tarde.', false],
    [new Error('detalle privado'), 'No se pudo completar la búsqueda. Intenta nuevamente.', false],
  ])('ruta infeliz: error de búsqueda %# se anuncia con mensaje seguro', async (error, message, notifies) => {
    const onAccessError = vi.fn()
    render(<Harness search={vi.fn().mockRejectedValue(error)} onAccessError={onAccessError} />)
    fireEvent.change(combobox(), { target: { value: 'a' } })

    expect(await screen.findByText(message)).toHaveClass('is-error')
    expect(screen.queryByRole('option')).not.toBeInTheDocument()
    expect(screen.queryByText('detalle privado')).not.toBeInTheDocument()
    expect(onAccessError).toHaveBeenCalledTimes(notifies ? 1 : 0)
  })

  it('ruta de borde: sin resultados, Escape cierra y luego limpia, editar anula la selección', async () => {
    const user = userEvent.setup()
    const search = vi.fn((term: string) => Promise.resolve(pageOf(term === 'zzz' ? [] : CLIENTS.slice(0, 1))))
    render(<Harness search={search} />)

    await user.type(combobox(), 'zzz')
    expect(await screen.findByText('No se encontraron clientes con ese texto.')).toBeInTheDocument()
    expect(screen.getByRole('listbox', { hidden: true })).not.toBeVisible()
    await user.keyboard('{Escape}')
    expect(combobox()).toHaveAttribute('aria-expanded', 'false')
    await user.keyboard('{Escape}')
    expect(combobox()).toHaveValue('')

    await user.type(combobox(), 'b')
    await screen.findByRole('option')
    await user.keyboard('{End}{Home}{ArrowUp}{Enter}')
    expect(screen.getByTestId('selected')).toHaveTextContent(CLIENTS[0].cliente_id)
    await user.type(combobox(), 'x')
    expect(screen.getByTestId('selected')).toHaveTextContent('ninguno')
    expect(combobox()).toHaveValue('Bodega Ficticia Nortex')
  })

  it('ruta de borde: ArrowDown abre la lista sin texto y Tab la cierra', async () => {
    const user = userEvent.setup()
    const search = vi.fn<(term: string, options: { signal?: AbortSignal }) => Promise<ClientPage>>(() => Promise.resolve(pageOf(CLIENTS)))
    render(<Harness search={search} />)
    combobox().focus()
    await user.keyboard('{ArrowDown}')
    await screen.findAllByRole('option')
    expect(search.mock.calls[0][0]).toBe('')
    expect(search.mock.calls[0][1].signal).toBeInstanceOf(AbortSignal)
    await user.keyboard('{Tab}')
    expect(combobox()).toHaveAttribute('aria-expanded', 'false')
  })
})
