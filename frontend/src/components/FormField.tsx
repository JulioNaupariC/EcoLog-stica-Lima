import type { ReactNode } from 'react'

interface Props {
  id: string
  label: string
  error?: string
  hint?: string
  children: ReactNode
}

export function FormField({ id, label, error, hint, children }: Props) {
  return <div className="form-field">
    <label htmlFor={id}>{label}</label>
    {hint ? <p className="field-hint" id={`${id}-hint`}>{hint}</p> : null}
    {children}
    {error ? <p className="field-error" id={`${id}-error`}>{error}</p> : null}
  </div>
}
