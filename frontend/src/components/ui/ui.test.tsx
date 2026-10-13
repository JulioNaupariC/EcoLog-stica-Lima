import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { Truck } from 'lucide-react'
import {
  Alert, Badge, Button, Card, DataTable, EmptyState, FormActions, FormSection, LinkButton, PageHeader,
  Skeleton, StatCard, StatusBadge, ToastProvider, useToast,
} from '.'

describe('Componentes de UI (ECL-22)', () => {
  it('Badge y StatusBadge comunican el estado con texto, no solo con color', () => {
    render(<>
      <StatusBadge status="VENCIDA" />
      <StatusBadge status="HABILITADO" />
      <Badge tone="sustain">Bajo CO₂</Badge>
      <Badge icon={null}>Próximamente</Badge>
    </>)
    expect(screen.getByText('Licencia vencida')).toHaveClass('badge--danger')
    expect(screen.getByText('Habilitado')).toHaveClass('badge--success')
    expect(screen.getByText('Bajo CO₂').querySelector('svg')).toHaveAttribute('aria-hidden', 'true')
    expect(screen.getByText('Próximamente').querySelector('svg')).toBeNull()
  })

  it('Button oculta el icono decorativo y LinkButton funciona con y sin router', () => {
    const { unmount } = render(<Button icon={Truck} variant="secondary" size="sm" block>Flota</Button>)
    const button = screen.getByRole('button', { name: 'Flota' })
    expect(button).toHaveAttribute('type', 'button')
    expect(button).toHaveClass('btn--secondary', 'btn--sm', 'btn--block')
    expect(button.querySelector('svg')).toHaveAttribute('aria-hidden', 'true')
    unmount()
    const standalone = render(<LinkButton to="/vehiculos">Vehículos</LinkButton>)
    expect(screen.getByRole('link', { name: 'Vehículos' })).toHaveAttribute('href', '/vehiculos')
    standalone.unmount()
    render(<MemoryRouter><LinkButton to="/vehiculos" icon={Truck}>Vehículos</LinkButton></MemoryRouter>)
    expect(screen.getByRole('link', { name: 'Vehículos' })).toHaveAttribute('href', '/vehiculos')
  })

  it('PageHeader muestra migas navegables y marca la página actual', () => {
    render(<MemoryRouter><PageHeader titleId="t" title="Vehículos" eyebrow="Flota" description="Detalle"
      breadcrumbs={[{ label: 'Inicio', to: '/' }, { label: 'Vehículos' }]} actions={<Button>Acción</Button>} /></MemoryRouter>)
    const crumbs = screen.getByRole('navigation', { name: 'Migas de pan' })
    expect(within(crumbs).getByRole('link', { name: 'Inicio' })).toHaveAttribute('href', '/')
    expect(within(crumbs).getByText('Vehículos')).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('heading', { level: 1, name: 'Vehículos' })).toBeInTheDocument()
  })

  it('Alert anuncia errores como alerta y el resto como estado', () => {
    render(<>
      <Alert tone="danger" title="Error">Detalle</Alert>
      <Alert tone="success">Hecho</Alert>
      <Alert tone="warning" role="note" actions={<Button>Reintentar</Button>}>Aviso</Alert>
    </>)
    expect(screen.getByRole('alert')).toHaveTextContent('ErrorDetalle')
    expect(screen.getByRole('status')).toHaveTextContent('Hecho')
    expect(screen.getByRole('note')).toHaveTextContent('Aviso')
  })

  it('DataTable conserva la semántica de tabla y etiqueta cada celda para la vista móvil', () => {
    render(<DataTable caption="Flota" label="Tabla de flota" rowKey={row => row.id}
      rows={[{ id: '1', placa: 'ABC-123', kg: '10' }]}
      columns={[
        { key: 'placa', header: 'Placa', primary: true, render: row => row.placa },
        { key: 'kg', header: 'Capacidad', align: 'end', render: row => row.kg },
      ]} />)
    const table = screen.getByRole('table', { name: 'Flota' })
    const [, row] = within(table).getAllByRole('row')
    const cells = within(row).getAllByRole('cell')
    expect(cells.map(cell => cell.dataset.label)).toEqual(['Placa', 'Capacidad'])
    expect(cells[1]).toHaveClass('is-end')
    expect(screen.getByRole('region', { name: 'Tabla de flota' })).toHaveAttribute('tabindex', '0')
  })

  it('Card, EmptyState, FormSection, FormActions, StatCard y Skeleton renderizan su estructura', () => {
    render(<>
      <Card title="Resumen" titleId="r" description="Datos" actions={<Button>Ir</Button>} tone="highlight">Contenido</Card>
      <EmptyState icon={Truck} title="Sin datos" action={<Button>Crear</Button>}>Nada aún</EmptyState>
      <FormSection legend="Carga" description="Peso y volumen"><input aria-label="Peso" /></FormSection>
      <FormActions><Button type="submit">Guardar</Button></FormActions>
      <StatCard icon={Truck} label="Vehículos" value={5} detail="3 activos" />
      <StatCard icon={Truck} label="Cargando" value="—" loading />
      <Skeleton lines={2} />
    </>)
    expect(screen.getByRole('region', { name: 'Resumen' })).toHaveClass('card--highlight')
    expect(screen.getByRole('heading', { name: 'Sin datos' })).toBeInTheDocument()
    expect(screen.getByRole('group', { name: 'Carga' })).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
    expect(screen.getByText('3 activos')).toBeInTheDocument()
    expect(document.querySelectorAll('.skeleton-line').length).toBeGreaterThanOrEqual(3)
  })

  it('Toast anuncia en una región viva, se cierra a mano y caduca sola', () => {
    vi.useFakeTimers()
    function Trigger() {
      const { notify } = useToast()
      return <button type="button" onClick={() => notify('Sesión cerrada.')}>Notificar</button>
    }
    render(<ToastProvider><Trigger /></ToastProvider>)
    const region = screen.getByLabelText('Notificaciones')
    expect(region).toHaveAttribute('aria-live', 'polite')
    fireEvent.click(screen.getByRole('button', { name: 'Notificar' }))
    expect(within(region).getByText('Sesión cerrada.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Cerrar notificación' }))
    expect(within(region).queryByText('Sesión cerrada.')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Notificar' }))
    act(() => { vi.advanceTimersByTime(5000) })
    expect(within(region).queryByText('Sesión cerrada.')).not.toBeInTheDocument()
    vi.useRealTimers()
  })

  it('useToast fuera de un proveedor no falla', () => {
    function Lonely() {
      const { notify } = useToast()
      return <button type="button" onClick={() => notify('x')}>Solo</button>
    }
    render(<Lonely />)
    expect(() => fireEvent.click(screen.getByRole('button', { name: 'Solo' }))).not.toThrow()
  })
})
