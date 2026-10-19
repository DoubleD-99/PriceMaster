import type { PropsWithChildren } from 'react'

export function Card({ children, title }: PropsWithChildren<{ title?: string }>) {
  return (
    <div className="card">
      {title && <h2>{title}</h2>}
      {children}
    </div>
  )
}
