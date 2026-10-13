import type { ReactNode } from 'react'
import { cx } from './cx'

export function Card({
  as: Tag = 'section', title, titleId, description, actions, children, className, tone, headingLevel = 2,
}: {
  as?: 'section' | 'article' | 'div'
  title?: ReactNode
  titleId?: string
  description?: ReactNode
  actions?: ReactNode
  children?: ReactNode
  className?: string
  tone?: 'highlight' | 'muted'
  headingLevel?: 2 | 3
}) {
  const Heading = headingLevel === 2 ? 'h2' : 'h3'
  return <Tag className={cx('card', tone && `card--${tone}`, className)}
    aria-labelledby={Tag !== 'div' && title && titleId ? titleId : undefined}>
    {title || actions ? <div className="card-header">
      <div className="card-heading">
        {title ? <Heading id={titleId} className="card-title">{title}</Heading> : null}
        {description ? <p className="card-description">{description}</p> : null}
      </div>
      {actions ? <div className="card-actions">{actions}</div> : null}
    </div> : null}
    {children}
  </Tag>
}
