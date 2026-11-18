import { useEffect, useRef, useState } from 'react'
import type { KeyboardEvent as ReactKeyboardEvent } from 'react'

export interface SelectOption {
  value: string
  label: string
  helper?: string
}

interface SelectProps {
  value: string
  options: readonly SelectOption[]
  onChange: (value: string) => void
  label: string
  placeholder?: string
  emptyMessage?: string
  fullWidth?: boolean
}

export function Select({
  value,
  options,
  onChange,
  label,
  placeholder = 'Не выбран',
  emptyMessage = 'Значений нет',
  fullWidth = false,
}: SelectProps) {
  const [open, setOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)
  const rootRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const selectedIndex = options.findIndex((option) => option.value === value)
  const valueLabel = selectedIndex >= 0 ? options[selectedIndex].label : placeholder

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

  function openMenu() {
    setActiveIndex(selectedIndex >= 0 ? selectedIndex : 0)
    setOpen(true)
  }

  function toggleMenu() {
    if (open) setOpen(false)
    else openMenu()
  }

  function choose(index: number) {
    const option = options[index]
    if (!option) return
    onChange(option.value)
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
      setActiveIndex((index) => Math.min(index + 1, options.length - 1))
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActiveIndex((index) => Math.max(index - 1, 0))
    } else if (event.key === 'Home') {
      event.preventDefault()
      setActiveIndex(0)
    } else if (event.key === 'End') {
      event.preventDefault()
      setActiveIndex(Math.max(options.length - 1, 0))
    } else if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      choose(activeIndex)
    } else if (event.key === 'Tab') {
      setOpen(false)
    }
  }

  return (
    <div ref={rootRef} className={`store-select${fullWidth ? ' store-select--field' : ''}`}>
      <button
        ref={triggerRef}
        type="button"
        className="store-select__trigger"
        aria-label={label}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={toggleMenu}
        onKeyDown={handleKeyDown}
      >
        <span className="store-select__meta">
          <span className="store-select__values">
            <span className="store-select__value">{valueLabel}</span>
            {options.map((option) => (
              <span key={option.value} className="store-select__ghost" aria-hidden="true">
                <span>{option.label}</span>
                {option.helper && <span className="store-select__option-code">{option.helper}</span>}
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
        <div className="store-select__menu" role="listbox" aria-label={label}>
          {options.length === 0 ? (
            <div className="store-select__note">{emptyMessage}</div>
          ) : (
            options.map((option, index) => (
              <button
                key={option.value}
                type="button"
                role="option"
                aria-selected={option.value === value}
                className={`store-select__option${index === activeIndex ? ' is-active' : ''}`}
                onMouseEnter={() => setActiveIndex(index)}
                onClick={() => choose(index)}
              >
                <span className="store-select__option-name">{option.label}</span>
                {option.helper && <span className="store-select__option-code">{option.helper}</span>}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  )
}
