import { useCallback, useEffect, useRef, useState } from 'react'
import type { KeyboardEvent as ReactKeyboardEvent } from 'react'

import { api } from '../api/client'
import { useStoreContext } from '../stores/storeContext'
import type { Store } from '../types/api'

export function StoreSelect() {
  const storeId = useStoreContext((state) => state.storeId)
  const setStoreId = useStoreContext((state) => state.setStoreId)
  const [stores, setStores] = useState<Store[]>([])
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)
  const [open, setOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(-1)
  const rootRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)

  const load = useCallback(() => {
    setLoading(true)
    setFailed(false)
    api
      .get<Store[]>('/stores')
      .then((response) => setStores(response.data))
      .catch(() => setFailed(true))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    let cancelled = false
    api
      .get<Store[]>('/stores')
      .then((response) => {
        if (!cancelled) setStores(response.data)
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!open) return
    function handlePointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handlePointerDown)
    return () => document.removeEventListener('mousedown', handlePointerDown)
  }, [open])

  const current = stores.find((store) => store.id === storeId) ?? null
  const valueLabel = current?.name ?? (storeId !== null ? `Магазин #${storeId}` : 'Не выбран')

  function openMenu() {
    const selectedIndex = stores.findIndex((store) => store.id === storeId)
    setActiveIndex(selectedIndex >= 0 ? selectedIndex : 0)
    setOpen(true)
  }

  function toggleMenu() {
    if (open) setOpen(false)
    else openMenu()
  }

  function selectStore(store: Store) {
    setStoreId(store.id)
    setOpen(false)
    triggerRef.current?.focus()
  }

  function handleKeyDown(event: ReactKeyboardEvent<HTMLButtonElement>) {
    if (!open) {
      if (event.key === 'ArrowDown' || event.key === 'Enter' || event.key === ' ') {
        event.preventDefault()
        openMenu()
      }
      return
    }

    if (event.key === 'Escape') {
      event.preventDefault()
      setOpen(false)
      triggerRef.current?.focus()
    } else if (event.key === 'ArrowDown') {
      event.preventDefault()
      setActiveIndex((index) => Math.min(index + 1, stores.length - 1))
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActiveIndex((index) => Math.max(index - 1, 0))
    } else if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      const store = stores[activeIndex]
      if (store) selectStore(store)
    } else if (event.key === 'Tab') {
      setOpen(false)
    }
  }

  return (
    <div className="store-select" ref={rootRef}>
      <button
        ref={triggerRef}
        type="button"
        className="store-select__trigger"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={toggleMenu}
        onKeyDown={handleKeyDown}
      >
        <span className="store-select__meta">
          <span className="store-select__values">
            <span className="store-select__value">{valueLabel}</span>
            {stores.map((store) => (
              <span key={store.id} className="store-select__ghost" aria-hidden="true">
                <span>{store.name}</span>
                <span className="store-select__option-code">#{store.id}</span>
              </span>
            ))}
          </span>
        </span>
        <svg
          className="store-select__chevron"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>

      {open && (
        <div className="store-select__menu" role="listbox" aria-label="Магазин">
          {loading && <div className="store-select__note">Загрузка магазинов…</div>}
          {!loading && failed && (
            <div className="store-select__note store-select__note--error">
              Не удалось загрузить
              <button type="button" className="store-select__retry" onClick={load}>
                Повторить
              </button>
            </div>
          )}
          {!loading && !failed && stores.length === 0 && (
            <div className="store-select__note">Магазины не найдены</div>
          )}
          {!loading &&
            !failed &&
            stores.map((store, index) => (
              <button
                key={store.id}
                type="button"
                role="option"
                aria-selected={store.id === storeId}
                className={`store-select__option${index === activeIndex ? ' is-active' : ''}`}
                onMouseEnter={() => setActiveIndex(index)}
                onClick={() => selectStore(store)}
              >
                <span className="store-select__option-name">{store.name}</span>
                <span className="store-select__option-code">#{store.id}</span>
              </button>
            ))}
        </div>
      )}
    </div>
  )
}
