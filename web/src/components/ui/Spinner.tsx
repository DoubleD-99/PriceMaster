export function Spinner({ label = 'Загрузка...' }: { label?: string }) {
  return (
    <div className="spinner-wrap">
      <span className="spinner" aria-label={label} />
      <span className="muted">{label}</span>
    </div>
  )
}
