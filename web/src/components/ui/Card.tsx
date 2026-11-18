import type { PropsWithChildren, ReactNode } from 'react'

export function Card({ children, title }: PropsWithChildren<{ title?: ReactNode }>) {
  return (
    <div className="card">
      {title && <h2>{title}</h2>}
      {children}
    </div>
  )
}
