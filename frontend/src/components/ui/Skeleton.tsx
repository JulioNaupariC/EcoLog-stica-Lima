import { cx } from './cx'

/** Visual placeholder only; pair it with a text status for assistive technologies. */
export function Skeleton({ lines = 3, variant = 'text', className }: {
  lines?: number
  variant?: 'text' | 'card'
  className?: string
}) {
  return <div className={cx('skeleton', `skeleton--${variant}`, className)} aria-hidden="true">
    {Array.from({ length: lines }, (_, index) => <span key={index} className="skeleton-line" />)}
  </div>
}
