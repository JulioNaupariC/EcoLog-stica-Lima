import type { ButtonHTMLAttributes, ReactNode, Ref } from 'react'
import { Link, useInRouterContext } from 'react-router-dom'
import type { LucideIcon } from 'lucide-react'
import { cx } from './cx'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'

interface CommonProps {
  variant?: ButtonVariant
  size?: 'md' | 'sm'
  icon?: LucideIcon
  block?: boolean
  children: ReactNode
}

function buttonClass(variant: ButtonVariant, size: 'md' | 'sm', block: boolean | undefined, className?: string) {
  return cx('btn', `btn--${variant}`, size === 'sm' && 'btn--sm', block && 'btn--block', className)
}

export function Button({
  variant = 'primary', size = 'md', icon: Icon, block, className, children, type = 'button', ref, ...rest
}: CommonProps & ButtonHTMLAttributes<HTMLButtonElement> & { ref?: Ref<HTMLButtonElement> }) {
  return <button ref={ref} type={type} className={buttonClass(variant, size, block, className)} {...rest}>
    {Icon ? <Icon aria-hidden="true" size={18} strokeWidth={2} /> : null}
    <span>{children}</span>
  </button>
}

export function LinkButton({
  to, variant = 'primary', size = 'md', icon: Icon, block, className, children,
}: CommonProps & { to: string, className?: string }) {
  const routed = useInRouterContext()
  const content = <>
    {Icon ? <Icon aria-hidden="true" size={18} strokeWidth={2} /> : null}
    <span>{children}</span>
  </>
  return routed
    ? <Link to={to} className={buttonClass(variant, size, block, className)}>{content}</Link>
    : <a href={to} className={buttonClass(variant, size, block, className)}>{content}</a>
}
