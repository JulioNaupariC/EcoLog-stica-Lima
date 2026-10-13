import { useEffect, useState } from 'react'
import { getDeliveryPreferences, PreferencesServiceError } from '../services/deliveryPreferences'
import type { DeliveryPreferences } from '../services/deliveryPreferences'

type LoadState =
  | { kind: 'loading' }
  | { kind: 'ready', preferences: DeliveryPreferences }
  | { kind: 'error', message: string }

interface Props {
  clientId: string
  orderReference: string
  onUseReference: (reference: string) => void
  load?: (clientId: string) => Promise<DeliveryPreferences>
}

function display(value: string | null): string {
  return value?.trim() ? value : 'Sin registrar'
}

/**
 * P8 / RF-005: shows the saved preferences of the selected client as context.
 * Schedule and access restriction are never copied into the order (RN-006);
 * the reference is copied only through an explicit action.
 */
export function ClientPreferencesProposal({
  clientId, orderReference, onUseReference, load = getDeliveryPreferences,
}: Props) {
  const [state, setState] = useState<LoadState>({ kind: 'loading' })
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    // The parent remounts this component per client (key), so state starts as loading.
    let current = true
    load(clientId).then(preferences => {
      if (current) setState({ kind: 'ready', preferences })
    }).catch((error: unknown) => {
      if (!current) return
      const message = error instanceof PreferencesServiceError && error.kind === 'forbidden'
        ? 'No tienes permisos para ver las preferencias de este cliente.'
        : 'No se pudieron cargar las preferencias del cliente. Puedes registrar el pedido igualmente.'
      setState({ kind: 'error', message })
    })
    return () => { current = false }
  }, [clientId, load])

  const headingId = `preferences-proposal-${clientId}`
  return <section className="preferences-proposal" aria-labelledby={headingId} aria-busy={state.kind === 'loading'}>
    <h2 id={headingId}>Preferencias del cliente</h2>
    <p className="preferences-proposal-note" aria-live="polite">
      {state.kind === 'loading' ? 'Cargando preferencias del cliente…' : null}
      {state.kind === 'error' ? state.message : null}
      {state.kind === 'ready' && copied ? 'Referencia copiada al pedido. Puedes editarla antes de registrar.' : null}
    </p>
    {state.kind === 'ready' ? <>
      <p className="preferences-proposal-note">
        Información guardada del cliente. No se copia al pedido salvo que uses la acción indicada.
      </p>
      <dl className="preferences-proposal-list">
        <div>
          <dt>Horario preferido</dt>
          <dd>{display(state.preferences.horario_preferido)}</dd>
          <dd className="preferences-proposal-hint">
            Solo informativo: la ventana del pedido se define en sus propios campos.
          </dd>
        </div>
        <div>
          <dt>Restricción de acceso</dt>
          <dd>{display(state.preferences.restriccion_acceso)}</dd>
        </div>
        <div>
          <dt>Referencia</dt>
          <dd>{display(state.preferences.referencia)}</dd>
          {state.preferences.referencia?.trim() ? <dd>
            <button type="button" className="preferences-secondary"
              disabled={orderReference === state.preferences.referencia}
              onClick={() => {
                onUseReference(state.preferences.referencia ?? '')
                setCopied(true)
              }}>Usar como referencia del pedido</button>
          </dd> : null}
        </div>
      </dl>
    </> : null}
  </section>
}
