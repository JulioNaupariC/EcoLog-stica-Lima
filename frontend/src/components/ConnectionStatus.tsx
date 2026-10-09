import { useOnlineStatus } from '../hooks/useOnlineStatus'

/** Does not claim that an API connection has been verified. */
export function ConnectionStatus() {
  const online = useOnlineStatus()
  return (
    <div role="status" aria-live="polite" aria-atomic="true" className={online ? 'connection-online' : 'connection-offline'}>
      {online ? 'Dispositivo conectado. La disponibilidad del servidor no está verificada.' : 'Sin conexión. Los datos previamente guardados podrían estar disponibles.'}
    </div>
  )
}
