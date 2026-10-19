export function Alert({
  type = 'info',
  children,
}: {
  type?: 'info' | 'success' | 'warning' | 'error'
  children: React.ReactNode
}) {
  return <div className={`alert alert--${type}`}>{children}</div>
}
