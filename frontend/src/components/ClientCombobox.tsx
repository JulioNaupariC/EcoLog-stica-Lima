import { useEffect, useId, useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'
import {
  CLIENT_SEARCH_MAX_LENGTH,
  ClientsServiceError,
  searchClients,
  shortClientId,
} from '../services/clients'
import type { ClientOption, ClientPage } from '../services/clients'
import './ClientCombobox.css'

type SearchStatus = 'idle' | 'loading' | 'ready' | 'error'

interface Props {
  id: string
  label: string
  hint?: string
  error?: string
  selected: ClientOption | null
  onSelect: (client: ClientOption | null) => void
  disabled?: boolean
  required?: boolean
  debounceMs?: number
  search?: (term: string, options: { signal?: AbortSignal }) => Promise<ClientPage>
  onAccessError?: (error: ClientsServiceError) => void
}

function resultMessage(count: number, total: number): string {
  if (count === 0) return 'No se encontraron clientes con ese texto.'
  const shown = count === 1 ? '1 cliente' : `${count} clientes`
  return total > count ? `${shown} de ${total}. Escribe más para acotar.` : `${shown} encontrado${count === 1 ? '' : 's'}.`
}

/**
 * Accessible client search following the WAI-ARIA combobox pattern
 * (editable input + listbox, focus stays on the input).
 */
export function ClientCombobox({
  id, label, hint, error, selected, onSelect, disabled = false, required = false,
  debounceMs = 250, search = searchClients, onAccessError,
}: Props) {
  const listId = useId()
  const statusId = `${id}-status`
  const [query, setQuery] = useState(selected?.nombre ?? '')
  const [options, setOptions] = useState<ClientOption[]>([])
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(-1)
  const [status, setStatus] = useState<SearchStatus>('idle')
  const [message, setMessage] = useState('')
  const [pending, setPending] = useState<{ term: string, sequence: number } | null>(null)
  const controller = useRef<AbortController | null>(null)
  const searchRef = useRef(search)
  const accessErrorRef = useRef(onAccessError)
  const [shownSelection, setShownSelection] = useState(selected)
  // Only a new external selection overwrites the text; clearing it keeps what was typed.
  if (selected !== shownSelection) {
    setShownSelection(selected)
    if (selected) setQuery(selected.nombre)
  }
  useEffect(() => {
    searchRef.current = search
    accessErrorRef.current = onAccessError
  })
  useEffect(() => () => controller.current?.abort(), [])

  useEffect(() => {
    if (pending === null) return undefined
    const timer = window.setTimeout(() => {
      controller.current?.abort()
      const current = new AbortController()
      controller.current = current
      setStatus('loading')
      setMessage('Buscando clientes…')
      searchRef.current(pending.term, { signal: current.signal }).then(page => {
        if (current.signal.aborted) return
        setOptions(page.items)
        setActive(page.items.length > 0 ? 0 : -1)
        setStatus('ready')
        setMessage(resultMessage(page.items.length, page.total))
      }).catch((reason: unknown) => {
        if (current.signal.aborted) return
        setOptions([])
        setActive(-1)
        setStatus('error')
        if (reason instanceof ClientsServiceError) {
          setMessage(reason.message)
          if (reason.kind === 'unauthorized' || reason.kind === 'forbidden') accessErrorRef.current?.(reason)
        } else {
          setMessage('No se pudo completar la búsqueda. Intenta nuevamente.')
        }
      })
    }, debounceMs)
    return () => window.clearTimeout(timer)
  }, [pending, debounceMs])

  function requestSearch(term: string) {
    setOpen(true)
    setPending(current => ({ term, sequence: (current?.sequence ?? 0) + 1 }))
  }

  function choose(option: ClientOption) {
    controller.current?.abort()
    setOpen(false)
    setActive(-1)
    setStatus('idle')
    setMessage('')
    setQuery(option.nombre)
    onSelect(option)
  }

  function close() {
    controller.current?.abort()
    setOpen(false)
    setActive(-1)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    const count = options.length
    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault()
        if (!open) { requestSearch(query); return }
        if (count > 0) setActive(index => (index + 1) % count)
        return
      case 'ArrowUp':
        event.preventDefault()
        if (open && count > 0) setActive(index => (index <= 0 ? count - 1 : index - 1))
        return
      case 'Home':
      case 'End':
        if (open && count > 0) {
          event.preventDefault()
          setActive(event.key === 'Home' ? 0 : count - 1)
        }
        return
      case 'Enter':
        if (open) {
          // Never submit the surrounding form while the list is open.
          event.preventDefault()
          if (active >= 0 && active < count) choose(options[active])
        }
        return
      case 'Escape':
        if (open) {
          event.preventDefault()
          close()
        } else if (query) {
          event.preventDefault()
          setQuery('')
          if (selected) onSelect(null)
        }
        return
      case 'Tab':
        close()
        return
      default:
    }
  }

  const describedBy = [hint ? `${id}-hint` : null, error ? `${id}-error` : null, statusId]
    .filter(Boolean).join(' ')
  const activeId = open && active >= 0 ? `${listId}-option-${active}` : undefined

  return <div className="form-field client-combobox">
    <label htmlFor={id}>{label}</label>
    {hint ? <p className="field-hint" id={`${id}-hint`}>{hint}</p> : null}
    <div className="client-combobox-control">
      <input
        id={id}
        type="text"
        role="combobox"
        autoComplete="off"
        spellCheck={false}
        maxLength={CLIENT_SEARCH_MAX_LENGTH}
        required={required}
        disabled={disabled}
        value={query}
        aria-autocomplete="list"
        aria-expanded={open}
        aria-controls={listId}
        aria-activedescendant={activeId}
        aria-invalid={Boolean(error)}
        aria-describedby={describedBy}
        onChange={event => {
          const value = event.target.value
          setQuery(value)
          if (selected) onSelect(null)
          requestSearch(value)
        }}
        onKeyDown={handleKeyDown}
        onBlur={close}
      />
      <ul id={listId} role="listbox" aria-label={`Resultados de ${label.toLowerCase()}`}
        className="client-combobox-list" hidden={!open || options.length === 0}>
        {options.map((option, index) => (
          <li
            key={option.cliente_id}
            id={`${listId}-option-${index}`}
            role="option"
            aria-selected={index === active}
            className="client-combobox-option"
            onMouseDown={event => event.preventDefault()}
            onClick={() => choose(option)}
          >
            <span className="client-combobox-name">{option.nombre}</span>
            <span className="client-combobox-id">ID {shortClientId(option.cliente_id)}…</span>
          </li>
        ))}
      </ul>
    </div>
    <p id={statusId} className={`client-combobox-status${status === 'error' ? ' is-error' : ''}`}
      aria-live="polite">
      {open ? message : ''}
    </p>
    {selected ? <p className="client-combobox-selected">
      Cliente seleccionado: <strong>{selected.nombre}</strong>{' '}
      <span className="client-combobox-id">(ID {shortClientId(selected.cliente_id)}…)</span>
    </p> : null}
    {error ? <p className="field-error" id={`${id}-error`}>{error}</p> : null}
  </div>
}
