import type { ReactNode } from 'react'
import { cx } from './cx'

/** Groups related fields with a visible legend and an optional explanation. */
export function FormSection({ legend, description, children, className }: {
  legend: ReactNode
  description?: ReactNode
  children: ReactNode
  className?: string
}) {
  return <fieldset className={cx('form-section', className)}>
    <legend className="form-section-legend">{legend}</legend>
    {description ? <p className="form-section-description">{description}</p> : null}
    <div className="form-section-body">{children}</div>
  </fieldset>
}

/** Primary actions; on narrow screens the bar sticks to the bottom of the viewport. */
export function FormActions({ children, className }: { children: ReactNode, className?: string }) {
  return <div className={cx('form-actions', className)}>{children}</div>
}
