import { act, render, screen } from '@testing-library/react'
import { useOnlineStatus } from './useOnlineStatus'

function Probe() {
  const online = useOnlineStatus()
  return <output aria-label="conexión">{online ? 'online' : 'offline'}</output>
}

describe('useOnlineStatus', () => {
  const initial = Object.getOwnPropertyDescriptor(window.navigator, 'onLine')
  afterEach(() => {
    if (initial) Object.defineProperty(window.navigator, 'onLine', initial)
    else Reflect.deleteProperty(window.navigator, 'onLine')
  })

  it('responde a eventos de desconexión y reconexión', async () => {
    Object.defineProperty(window.navigator, 'onLine', { configurable: true, value: true })
    render(<Probe />)
    expect(screen.getByLabelText('conexión')).toHaveTextContent('online')
    Object.defineProperty(window.navigator, 'onLine', { configurable: true, value: false })
    await act(async () => {
      window.dispatchEvent(new Event('offline'))
      await Promise.resolve()
    })
    expect(screen.getByLabelText('conexión')).toHaveTextContent('offline')
    Object.defineProperty(window.navigator, 'onLine', { configurable: true, value: true })
    await act(async () => {
      window.dispatchEvent(new Event('online'))
      await Promise.resolve()
    })
    expect(screen.getByLabelText('conexión')).toHaveTextContent('online')
  })
})
