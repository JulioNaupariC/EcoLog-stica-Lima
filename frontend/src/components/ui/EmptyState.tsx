import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'

export function EmptyState({ icon: Icon, title, children, action, headingLevel = 2, titleId }: {
  icon: LucideIcon
  title: ReactNode
  children?: ReactNode
  action?: ReactNode
  headingLevel?: 1 | 2 | 3
  titleId?: string
}) {
  const Heading = headingLevel === 1 ? 'h1' : headingLevel === 2 ? 'h2' : 'h3'
  return <div className="empty-state">
    <span className="empty-state-icon"><Icon aria-hidden="true" size={28} /></span>
    <Heading id={titleId} className="empty-state-title" tabIndex={headingLevel === 1 ? -1 : undefined}>{title}</Heading>
    {children ? <div className="empty-state-text">{children}</div> : null}
    {action ? <div className="empty-state-action">{action}</div> : null}
  </div>
}
