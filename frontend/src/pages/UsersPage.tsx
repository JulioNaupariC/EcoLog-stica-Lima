import { useCallback, useEffect, useRef, useState } from 'react'
import { ChevronLeft, ChevronRight, Copy, KeyRound, RefreshCw, Users } from 'lucide-react'
import { Alert, Badge, Button, DataTable, Dialog, EmptyState, PageHeader, Skeleton, StatusBadge } from '../components/ui'
import type { Column } from '../components/ui'
import { ROLE_LABEL } from '../domain/roles'
import { listUsers, resetPassword, UserServiceError } from '../services/users'
import type { TemporaryPassword, UserListItem, UserPage } from '../services/users'

const PAGE_SIZE = 20
const RESET_FAILED = 'No se pudo restablecer. Intenta de nuevo o revisa tu conexión.'
interface ListState { status: 'loading' | 'ready' | 'error'; result: UserPage | null; error: string }
type Step =
  | { kind: 'confirm'; user: UserListItem; busy: boolean; error: string }
  | { kind: 'show'; user: UserListItem; temporary: TemporaryPassword; copy: '' | 'copied' | 'failed' }
  | null

function stateBadge(user: UserListItem) {
  if (user.estado === 'BLOQUEADO') return <Badge tone="warning">Bloqueado</Badge>
  return <StatusBadge status={user.estado} />
}

/** ECL-77: Administrator-only account list with the one-time temporary password. */
export function UsersPage({ ownId, onSessionExpired }: { ownId: string; onSessionExpired: () => void }) {
  const [list, setList] = useState<ListState>({ status: 'loading', result: null, error: '' })
  const [page, setPage] = useState(1)
  const [step, setStep] = useState<Step>(null)
  const opener = useRef<HTMLButtonElement | null>(null)
  const cancelButton = useRef<HTMLButtonElement>(null)
  const doneButton = useRef<HTMLButtonElement>(null)
  const requestNumber = useRef(0)

  const load = useCallback(async (nextPage: number) => {
    const number = ++requestNumber.current
    setPage(nextPage)
    setList({ status: 'loading', result: null, error: '' })
    try {
      const result = await listUsers(nextPage, PAGE_SIZE)
      if (number === requestNumber.current) setList({ status: 'ready', result, error: '' })
    } catch (error) {
      if (number !== requestNumber.current) return
      if (error instanceof UserServiceError && error.kind === 'unauthorized') onSessionExpired()
      setList({ status: 'error', result: null,
        error: error instanceof UserServiceError ? error.message : 'No se pudo cargar el listado.' })
    }
  }, [onSessionExpired])

  useEffect(() => {
    const requests = requestNumber
    void Promise.resolve().then(() => load(1))
    return () => { requests.current++ }
  }, [load])

  async function confirmReset() {
    if (step?.kind !== 'confirm' || step.busy) return
    const { user } = step
    setStep({ ...step, busy: true, error: '' })
    try {
      const temporary = await resetPassword(user.usuario_id)
      setStep({ kind: 'show', user, temporary, copy: '' })
    } catch (error) {
      if (error instanceof UserServiceError && error.kind === 'unauthorized') { setStep(null); onSessionExpired(); return }
      const detail = error instanceof UserServiceError && ['not_found', 'conflict', 'forbidden'].includes(error.kind)
        ? error.message : RESET_FAILED
      setStep({ kind: 'confirm', user, busy: false, error: detail })
    }
  }

  async function copyTemporary() {
    if (step?.kind !== 'show') return
    try {
      await navigator.clipboard.writeText(step.temporary.contrasena_temporal)
      setStep({ ...step, copy: 'copied' })
    } catch {
      setStep({ ...step, copy: 'failed' })
    }
  }

  function finish() {
    if (step?.kind !== 'show') return
    const resetId = step.user.usuario_id
    // The temporary password leaves the component state here and is not kept anywhere.
    setStep(null)
    // Mirror the server state in place: reloading would unmount the row and lose focus.
    setList(current => current.result ? { ...current, result: { ...current.result,
      items: current.result.items.map(item => item.usuario_id === resetId
        ? { ...item, debe_cambiar_contrasena: true } : item) } } : current)
  }

  const columns: Column<UserListItem>[] = [
    { key: 'email', header: 'Correo', primary: true, render: user => user.email },
    { key: 'rol', header: 'Rol', render: user => ROLE_LABEL[user.rol] },
    { key: 'estado', header: 'Estado', render: user => <span className="badge-row">
      {stateBadge(user)}
      {user.debe_cambiar_contrasena ? <Badge tone="info" icon={KeyRound}>Debe cambiar contraseña</Badge> : null}
    </span> },
    { key: 'acciones', header: 'Acciones', align: 'end', render: user => {
      const own = user.usuario_id === ownId
      const inactive = user.estado === 'INACTIVO'
      return <Button variant="secondary" size="sm" icon={KeyRound} disabled={own || inactive || step !== null}
        aria-label={`Restablecer contraseña de ${user.email}`}
        title={own ? 'Usa «Cambiar contraseña» en tu menú de cuenta' : inactive ? 'La cuenta está inactiva' : undefined}
        onClick={event => { opener.current = event.currentTarget; setStep({ kind: 'confirm', user, busy: false, error: '' }) }}>
        Restablecer contraseña
      </Button>
    } },
  ]
  const totalPages = Math.max(1, Math.ceil((list.result?.total ?? 0) / PAGE_SIZE))

  return <section className="users-page" aria-labelledby="users-title">
    <PageHeader titleId="users-title" title="Usuarios" eyebrow="Administración"
      breadcrumbs={[{ label: 'Inicio', to: '/' }, { label: 'Usuarios' }]}
      description="Restablece la contraseña de quien la olvidó. La persona recibirá una contraseña temporal y deberá cambiarla al entrar." />
    <section className="card" aria-labelledby="user-list-title" aria-busy={list.status === 'loading'}>
      <div className="card-header">
        <div className="card-heading">
          <h2 id="user-list-title" className="card-title">Cuentas registradas</h2>
          {list.status === 'ready' && list.result ? <p className="card-description">
            {list.result.total} {list.result.total === 1 ? 'cuenta' : 'cuentas'}
          </p> : null}
        </div>
        <div className="card-actions">
          <Button variant="secondary" size="sm" icon={RefreshCw} disabled={list.status === 'loading'}
            onClick={() => { void load(page) }}>Actualizar listado</Button>
        </div>
      </div>
      {list.status === 'loading' ? <>
        <p className="field-hint" role="status">Cargando cuentas…</p>
        <Skeleton variant="card" />
      </> : null}
      {list.status === 'error' ? <Alert tone="danger" title="No se pudo cargar el listado."
        actions={<Button variant="secondary" size="sm" onClick={() => { void load(page) }}>Reintentar carga</Button>}>
        {list.error}
      </Alert> : null}
      {list.status === 'ready' && list.result ? <>
        {list.result.items.length === 0
          ? <EmptyState icon={Users} headingLevel={3} title="Sin cuentas en esta página">
            <p role="status">Vuelve a la primera página o actualiza el listado.</p>
          </EmptyState>
          : <DataTable columns={columns} rows={list.result.items} rowKey={user => user.usuario_id}
            caption="Cuentas de usuario con su rol y estado" label="Cuentas registradas" />}
        <nav className="pagination" aria-label="Páginas de usuarios">
          <Button variant="secondary" size="sm" icon={ChevronLeft} disabled={page <= 1} onClick={() => { void load(page - 1) }}>Anterior</Button>
          <span>Página {page} de {totalPages}</span>
          <Button variant="secondary" size="sm" icon={ChevronRight} disabled={page >= totalPages} onClick={() => { void load(page + 1) }}>Siguiente</Button>
        </nav>
      </> : null}
    </section>

    {step?.kind === 'confirm' ? <Dialog role="alertdialog" title="Restablecer contraseña"
      returnFocus={opener} initialFocus={cancelButton} onClose={() => { if (!step.busy) setStep(null) }}
      actions={<>
        <Button ref={cancelButton} variant="secondary" disabled={step.busy} onClick={() => setStep(null)}>Cancelar</Button>
        <Button variant="danger" icon={KeyRound} disabled={step.busy} onClick={() => { void confirmReset() }}>
          {step.busy ? 'Restableciendo…' : 'Restablecer'}
        </Button>
      </>}>
      <p>¿Restablecer la contraseña de <strong>{step.user.email}</strong>? Se cerrarán sus sesiones activas.</p>
      {step.error ? <Alert tone="danger">{step.error}</Alert> : null}
    </Dialog> : null}

    {step?.kind === 'show' ? <Dialog title="Contraseña temporal" returnFocus={opener} initialFocus={doneButton}
      onClose={finish}
      actions={<Button ref={doneButton} onClick={finish}>Listo</Button>}>
      <p>Entrégala a <strong>{step.user.email}</strong> por un canal seguro. Al entrar deberá elegir una nueva.</p>
      <div className="temporary-password">
        <code className="temporary-password-value" data-testid="temporary-password">{step.temporary.contrasena_temporal}</code>
        <Button variant="secondary" size="sm" icon={Copy} onClick={() => { void copyTemporary() }}>Copiar</Button>
      </div>
      {step.copy === 'copied' ? <p className="field-hint" role="status">Contraseña copiada.</p> : null}
      {step.copy === 'failed' ? <p className="field-hint" role="status">No se pudo copiar. Selecciona la contraseña y cópiala manualmente.</p> : null}
      <Alert tone="warning" role="note">No se volverá a mostrar · vence en 24 h</Alert>
    </Dialog> : null}
  </section>
}
