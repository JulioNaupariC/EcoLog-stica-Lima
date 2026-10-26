import { useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { KeyRound, LogOut } from 'lucide-react'
import { Alert, Button, FormActions } from '../components/ui'
import { FormField } from '../components/FormField'
import { changePassword, MIN_PASSWORD_LENGTH, UserServiceError } from '../services/users'
import { PASSWORD_FIELDS as FIELDS, validatePasswordField } from '../domain/passwordForm'
import type { PasswordErrors as Errors, PasswordField as Field, PasswordValues as Values } from '../domain/passwordForm'

/**
 * ECL-77: mandatory after signing in with a temporary password, voluntary from
 * the account menu. Passwords live only in this form's state until submitted.
 */
export function ChangePasswordPage({ required, onChanged, onSessionExpired, onLogout }: {
  required: boolean
  onChanged: () => void
  onSessionExpired: () => void
  onLogout?: () => void
}) {
  const [values, setValues] = useState<Values>({ current: '', next: '', confirm: '' })
  const [errors, setErrors] = useState<Errors>({})
  const [globalError, setGlobalError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const inputs = { current: useRef<HTMLInputElement>(null), next: useRef<HTMLInputElement>(null), confirm: useRef<HTMLInputElement>(null) }
  const currentLabel = required ? 'Contraseña temporal' : 'Contraseña actual'

  function update(field: Field, value: string) {
    const next = { ...values, [field]: value }
    setValues(next)
    setGlobalError('')
    // Errors appear on blur; while one is shown, it clears as soon as the value is fixed.
    setErrors(current => {
      const updated = { ...current }
      for (const name of FIELDS) {
        if (updated[name] && !validatePasswordField(name, next)) delete updated[name]
      }
      return updated
    })
  }

  function blur(field: Field) {
    if (!values[field] && field !== 'current') return
    setErrors(current => ({ ...current, [field]: validatePasswordField(field, values) }))
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (submitting) return
    const found: Errors = {}
    for (const field of FIELDS) found[field] = validatePasswordField(field, values)
    setErrors(found)
    const first = FIELDS.find(field => found[field])
    if (first) { inputs[first].current?.focus(); return }
    setSubmitting(true)
    setGlobalError('')
    try {
      await changePassword(values.current, values.next)
      setValues({ current: '', next: '', confirm: '' })
      onChanged()
    } catch (error) {
      if (error instanceof UserServiceError && error.kind === 'unauthorized') { onSessionExpired(); return }
      if (error instanceof UserServiceError && error.kind === 'current_invalid') {
        setErrors({ current: error.message })
        setValues(current => ({ ...current, current: '' }))
        inputs.current.current?.focus()
      } else {
        setGlobalError(error instanceof UserServiceError ? error.message
          : 'No se pudo guardar la contraseña. Intenta de nuevo o revisa tu conexión.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  function input(field: Field, id: string, autoComplete: string) {
    const describedBy = [field === 'next' ? `${id}-hint` : '', errors[field] ? `${id}-error` : ''].filter(Boolean).join(' ')
    return <input id={id} ref={inputs[field]} type="password" autoComplete={autoComplete} required
      maxLength={128} value={values[field]} aria-invalid={Boolean(errors[field])}
      aria-describedby={describedBy || undefined}
      onChange={event => update(field, event.target.value)} onBlur={() => blur(field)} />
  }

  return <section className={required ? 'auth-panel change-password-page' : 'change-password-page'} aria-labelledby="change-password-title">
    <div className={required ? 'auth-card' : 'card'}>
      <p className="eyebrow">{required ? 'Acceso' : 'Cuenta'}</p>
      <h1 id="change-password-title">Cambiar contraseña</h1>
      <p className="page-description">{required
        ? 'Entraste con una contraseña temporal. Elige una nueva para continuar; solo tú la conocerás.'
        : 'Elige una contraseña nueva. Se cerrarán tus otras sesiones abiertas.'}</p>
      {globalError ? <Alert tone="danger">{globalError}</Alert> : null}
      <form className="form-stack" noValidate aria-busy={submitting} onSubmit={event => { void submit(event) }}>
        <FormField id="password-current" label={currentLabel} error={errors.current}>
          {input('current', 'password-current', 'current-password')}
        </FormField>
        <FormField id="password-next" label={`Nueva contraseña (mínimo ${MIN_PASSWORD_LENGTH} caracteres)`}
          hint="Usa una frase fácil de recordar para ti y difícil de adivinar." error={errors.next}>
          {input('next', 'password-next', 'new-password')}
        </FormField>
        <FormField id="password-confirm" label="Confirmar nueva contraseña" error={errors.confirm}>
          {input('confirm', 'password-confirm', 'new-password')}
        </FormField>
        {submitting ? <p className="field-hint" role="status">Guardando contraseña…</p> : null}
        <FormActions>
          {onLogout ? <Button variant="ghost" icon={LogOut} onClick={onLogout}>Cerrar sesión</Button> : null}
          <Button type="submit" icon={KeyRound} disabled={submitting}>
            {submitting ? 'Guardando…' : 'Guardar contraseña'}
          </Button>
        </FormActions>
      </form>
    </div>
  </section>
}
