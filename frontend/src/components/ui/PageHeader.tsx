import type { ReactNode, Ref } from 'react'
import { Link, useInRouterContext } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'

export interface Crumb { label: string, to?: string }

export function PageHeader({ breadcrumbs, title, titleId, description, actions, eyebrow, titleRef }: {
  breadcrumbs?: Crumb[]
  title: ReactNode
  titleId: string
  description?: ReactNode
  actions?: ReactNode
  eyebrow?: ReactNode
  titleRef?: Ref<HTMLHeadingElement>
}) {
  // Pages are also rendered standalone (tests, previews) without a router.
  const routed = useInRouterContext()
  return <header className="page-header">
    {breadcrumbs?.length ? <nav aria-label="Migas de pan" className="breadcrumbs">
      <ol>
        {breadcrumbs.map((crumb, index) => {
          const last = index === breadcrumbs.length - 1
          return <li key={crumb.label}>
            {crumb.to && !last ? (routed ? <Link to={crumb.to}>{crumb.label}</Link> : <a href={crumb.to}>{crumb.label}</a>)
              : <span aria-current={last ? 'page' : undefined}>{crumb.label}</span>}
            {!last ? <ChevronRight aria-hidden="true" size={14} /> : null}
          </li>
        })}
      </ol>
    </nav> : null}
    <div className="page-header-row">
      <div className="page-header-text">
        {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
        <h1 id={titleId} ref={titleRef} tabIndex={titleRef ? -1 : undefined}>{title}</h1>
        {description ? <p className="page-description">{description}</p> : null}
      </div>
      {actions ? <div className="page-header-actions">{actions}</div> : null}
    </div>
  </header>
}
