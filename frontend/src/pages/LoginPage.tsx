import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Leaf, LogIn, MapPinned, ShieldCheck, WifiOff } from 'lucide-react'
import { Alert, Button } from '../components/ui'
import {
  AuthServiceError,
  login,
} from '../services/auth'
import type { LoginRequest, LoginResponse } from '../services/auth'

type FieldErrors = Partial<Record<keyof LoginRequest, string>>

interface LoginPageProps {
  onLoginSuccess: (identity: LoginResponse, email: string) => void
  /** Message from a previous session (expired session, logout issue). */
  notice?: string
}

export function LoginPage({ onLoginSuccess, notice }: LoginPageProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<FieldErrors>({})
  const [globalError, setGlobalError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const submittingRef = useRef(false)
  const emailRef = useRef<HTMLInputElement>(null)
  const passwordRef = useRef<HTMLInputElement>(null)
  const errorRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (globalError && !errors.email && !errors.password) {
      errorRef.current?.focus()
    }
  }, [errors.email, errors.password, globalError])

  function updateEmail(value: string) {
    setEmail(value)
    setErrors((current) => ({ ...current, email: undefined }))
    setGlobalError('')
  }

  function updatePassword(value: string) {
    setPassword(value)
    setErrors((current) => ({ ...current, password: undefined }))
    setGlobalError('')
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (submittingRef.current) return

    const nextErrors: FieldErrors = {}
    if (!email) {
      nextErrors.email = 'El correo electrónico es obligatorio.'
    } else if (email.length > 255) {
      nextErrors.email = 'El correo electrónico no puede superar 255 caracteres.'
    }
    if (!password) {
      nextErrors.password = 'La contraseña es obligatoria.'
    }
    setErrors(nextErrors)
    if (nextErrors.email || nextErrors.password) {
      setGlobalError('Revisa los datos ingresados.')
      if (nextErrors.email) emailRef.current?.focus()
      else passwordRef.current?.focus()
      return
    }

    submittingRef.current = true
    setSubmitting(true)
    setGlobalError('')
    let identity: LoginResponse | null = null
    const submittedEmail = email.trim()
    try {
      identity = await login({ email, password })
    } catch (error) {
      if (error instanceof AuthServiceError) {
        const fieldErrors: FieldErrors = {}
        for (const issue of error.issues) {
          fieldErrors[issue.field] = issue.message
        }
        setErrors(fieldErrors)
        setGlobalError(error.message)
        if (fieldErrors.email) emailRef.current?.focus()
        else if (fieldErrors.password) passwordRef.current?.focus()
      } else {
        setErrors({})
        setGlobalError('No se pudo iniciar sesión.')
      }
    } finally {
      setPassword('')
      submittingRef.current = false
      setSubmitting(false)
    }
    if (identity) onLoginSuccess(identity, submittedEmail)
  }

  return (
    <div className="auth-layout">
      <aside className="auth-brand" aria-label="EcoLogística Lima">
        <p className="brand">
          <span className="brand-mark" aria-hidden="true"><Leaf size={18} /></span>
          <span className="brand-text">EcoLogística Lima</span>
        </p>
        <p className="auth-brand-title">Operación logística sostenible para DistriRápido.</p>
        <ul className="auth-brand-points">
          <li><MapPinned aria-hidden="true" size={20} /><span>Pedidos, flota y conductores en un solo lugar.</span></li>
          <li><WifiOff aria-hidden="true" size={20} /><span>Itinerario del conductor disponible sin conexión.</span></li>
          <li><ShieldCheck aria-hidden="true" size={20} /><span>Acceso por rol y operaciones auditadas.</span></li>
        </ul>
      </aside>
      <section className="auth-panel login-page" aria-labelledby="login-title">
        <div className="auth-card">
          <p className="eyebrow">Acceso</p>
          <h1 id="login-title">Iniciar sesión</h1>
          <p className="page-description">Ingresa tus credenciales para acceder a la aplicación.</p>

          {notice && !globalError ? <Alert tone="danger">{notice}</Alert> : null}
          {globalError ? (
            <Alert tone="danger" ref={errorRef} tabIndex={-1}>{globalError}</Alert>
          ) : null}

          <form
            className="form-stack login-form"
            noValidate
            aria-busy={submitting}
            onSubmit={(event) => { void handleSubmit(event) }}
          >
            <div className="form-field">
              <label htmlFor="login-email">Correo electrónico</label>
              <input
                id="login-email"
                name="email"
                type="text"
                inputMode="email"
                autoComplete="username"
                maxLength={255}
                required
                ref={emailRef}
                value={email}
                aria-invalid={Boolean(errors.email)}
                aria-describedby={errors.email ? 'login-email-error' : undefined}
                onChange={(event) => updateEmail(event.target.value)}
              />
              {errors.email ? <p className="field-error" id="login-email-error">{errors.email}</p> : null}
            </div>

            <div className="form-field">
              <label htmlFor="login-password">Contraseña</label>
              <input
                id="login-password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                ref={passwordRef}
                value={password}
                aria-invalid={Boolean(errors.password)}
                aria-describedby={errors.password ? 'login-password-error' : undefined}
                onChange={(event) => updatePassword(event.target.value)}
              />
              {errors.password ? <p className="field-error" id="login-password-error">{errors.password}</p> : null}
            </div>

            {submitting ? <p className="field-hint" role="status">Iniciando sesión…</p> : null}
            <Button type="submit" icon={LogIn} disabled={submitting} block>
              {submitting ? 'Iniciando sesión…' : 'Iniciar sesión'}
            </Button>
          </form>
        </div>
      </section>
    </div>
  )
}
