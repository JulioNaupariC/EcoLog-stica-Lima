import { useEffect, useRef, useState } from 'react'
import { Alert, Button, Dialog } from './ui'
import { AuthServiceError, extendSession } from '../services/auth'
import type { LoginResponse, SessionExtension } from '../services/auth'

const WARNING_MS = 120_000

export function SessionExpiryNotice({ identity, onExtended, onExpired, onLogout, onSaveAndExit }: {
  identity: LoginResponse
  onExtended: (extension: SessionExtension) => void
  onExpired: () => void
  onLogout: () => void
  onSaveAndExit: () => void
}) {
  const [warning, setWarning] = useState(false)
  const [open, setOpen] = useState(false)
  const [pending, setPending] = useState(false)
  const [limit, setLimit] = useState(false)
  const [error, setError] = useState('')
  const request = useRef(0)

  useEffect(() => () => { request.current += 1 }, [])
  useEffect(() => {
    if (!identity.expires_at) return
    const expires = Date.parse(identity.expires_at)
    function check() {
      if (Date.now() >= expires) onExpired()
      else if (Date.now() >= expires - WARNING_MS) { setWarning(true); setOpen(true) }
    }
    const warningTimer = setTimeout(check, Math.max(0, expires - WARNING_MS - Date.now()))
    const expiryTimer = setTimeout(check, Math.max(0, expires - Date.now()))
    // Sleeping/background tabs recheck the deadline as soon as they resume.
    window.addEventListener('focus', check)
    document.addEventListener('visibilitychange', check)
    return () => {
      clearTimeout(warningTimer); clearTimeout(expiryTimer)
      window.removeEventListener('focus', check)
      document.removeEventListener('visibilitychange', check)
    }
  }, [identity.expires_at, onExpired])

  async function renew() {
    if (pending) return
    const current = ++request.current
    setPending(true); setError('')
    try {
      const extension = await extendSession()
      if (current !== request.current) return
      if (Date.parse(extension.expires_at) <= Date.now()) { onExpired(); return }
      onExtended(extension)
      setWarning(false); setOpen(false); setLimit(false)
    } catch (caught) {
      if (current !== request.current) return
      if (caught instanceof AuthServiceError && caught.status === 401) { onExpired(); return }
      if (caught instanceof AuthServiceError && caught.status === 409) {
        setLimit(true)
        setError('La sesión alcanzó su duración máxima; vuelve a iniciar sesión.')
      } else {
        setError('No se pudo renovar la sesión. Comprueba tu conexión e inténtalo antes del vencimiento.')
      }
    } finally {
      if (current === request.current) setPending(false)
    }
  }

  return <>
    {warning && !open ? <Alert tone="warning" role="status"
      actions={<Button onClick={() => setOpen(true)}>Revisar vencimiento</Button>}>
      Tu sesión vence pronto. Guarda tu trabajo o amplía el tiempo.
    </Alert> : null}
    {open ? <Dialog role="alertdialog" title="Tu sesión está por vencer" onClose={() => setOpen(false)}
      actions={<>
        {!limit ? <Button disabled={pending} onClick={() => { void renew() }}>
          {pending ? 'Renovando sesión…' : 'Seguir conectado'}
        </Button> : <Button disabled={pending} onClick={onSaveAndExit}>Guardar borrador y volver a entrar</Button>}
        <Button variant="secondary" disabled={pending} onClick={onLogout}>Cerrar sesión</Button>
        <Button variant="ghost" onClick={() => setOpen(false)}>Volver al formulario</Button>
      </>}>
      <p>Tu sesión vence en menos de dos minutos. Puedes seguir conectado o cerrar sesión.</p>
      {error ? <p role="alert">{error}</p> : null}
      {limit ? <p>Ya no se puede extender. Guarda el borrador antes de volver a entrar. Las contraseñas no se guardan.</p> : null}
    </Dialog> : null}
  </>
}
