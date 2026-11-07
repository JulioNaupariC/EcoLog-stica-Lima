import { act, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import type { ReactElement } from 'react'
import { App } from './App'

const page = vi.hoisted(() => {
  let resolve!: (module: { HomePage: () => ReactElement }) => void
  const promise = new Promise<{ HomePage: () => ReactElement }>(ready => { resolve = ready })
  return { promise, resolve }
})
vi.mock('../pages/HomePage', () => page.promise)
vi.mock('../services/offlineAccess', () => ({
  recallDriver: () => ({ usuario_id: '123e4567-e89b-42d3-a456-426614174000', rol: 'CONDUCTOR' }),
  rememberDriver: vi.fn(), forgetDriver: vi.fn(),
}))
vi.mock('../hooks/useIncidentSynchronization', () => ({ useIncidentSynchronization: vi.fn() }))

it('anuncia el chunk pendiente sin ocultar el shell y titula la página al resolver', async () => {
  render(<MemoryRouter><App /></MemoryRouter>)
  expect(screen.getByRole('status')).toHaveTextContent('Cargando página…')
  expect(screen.getByRole('link', { name: 'Mi itinerario' })).toBeInTheDocument()
  await act(async () => {
    page.resolve({ HomePage: () => <h1>Inicio cargado</h1> })
    await page.promise
  })
  expect(await screen.findByRole('heading', { name: 'Inicio cargado' })).toBeInTheDocument()
  expect(screen.queryByText('Cargando página…')).not.toBeInTheDocument()
  await waitFor(() => expect(document.title).toBe('Inicio cargado — EcoLogística Lima'))
})
