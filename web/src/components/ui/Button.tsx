import type { ButtonHTMLAttributes, PropsWithChildren } from 'react'

export function Button({
  children,
  className = '',
  variant = 'primary',
  ...props
}: PropsWithChildren<ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'ghost' | 'success' | 'danger' }>) {
  const base = 'btn'
  const variants = {
    primary: 'btn--primary',
    ghost: 'btn--ghost',
    success: 'btn--success',
    danger: 'btn--danger',
  } as const
  return (
    <button className={`${base} ${variants[variant]} ${className}`.trim()} {...props}>
      {children}
    </button>
  )
}
