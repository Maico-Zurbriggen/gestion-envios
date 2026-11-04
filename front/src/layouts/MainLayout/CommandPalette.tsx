import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { CornerDownLeft, Search, type LucideIcon } from 'lucide-react'

export interface CommandItem {
  id: string
  label: string
  description: string
  icon: LucideIcon
  group: string
  keywords?: string
  run: () => void
}

interface CommandPaletteProps {
  open: boolean
  items: CommandItem[]
  onClose: () => void
}

function normalize(text: string) {
  return text.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
}

/** Buscador rápido (Ctrl + K): lleva a cualquier sección o ejecuta una acción. */
export function CommandPalette({ open, items, onClose }: CommandPaletteProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  return (
    <dialog
      ref={dialogRef}
      className="command-palette"
      aria-label="Buscador rápido"
      onCancel={(event) => {
        event.preventDefault()
        onClose()
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      {open ? <PaletteContent items={items} onClose={onClose} /> : null}
    </dialog>
  )
}

function PaletteContent({ items, onClose }: Omit<CommandPaletteProps, 'open'>) {
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)
  const listRef = useRef<HTMLUListElement>(null)
  const terms = normalize(query).split(/\s+/).filter(Boolean)
  const results = items.filter((item) => {
    const haystack = normalize(`${item.label} ${item.description} ${item.keywords ?? ''} ${item.group}`)
    return terms.every((term) => haystack.includes(term))
  })
  const current = Math.min(active, Math.max(results.length - 1, 0))

  function run(item: CommandItem | undefined) {
    if (!item) return
    onClose()
    item.run()
  }

  function move(delta: number) {
    if (!results.length) return
    const next = (current + delta + results.length) % results.length
    setActive(next)
    listRef.current?.querySelector(`[data-index="${next}"]`)?.scrollIntoView({ block: 'nearest' })
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      move(1)
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      move(-1)
    } else if (event.key === 'Enter') {
      event.preventDefault()
      run(results[current])
    }
  }

  let lastGroup = ''

  return (
    <div className="command-palette__panel">
      <div className="command-palette__search">
        <Search size={18} aria-hidden="true" />
        <input
          type="text"
          role="combobox"
          aria-expanded="true"
          aria-controls="command-palette-results"
          aria-activedescendant={results[current] ? `command-${results[current].id}` : undefined}
          aria-label="Buscar secciones y acciones"
          placeholder="Buscar secciones y acciones…"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value)
            setActive(0)
          }}
          onKeyDown={handleKeyDown}
          autoFocus
        />
        <kbd>Esc</kbd>
      </div>
      <ul className="command-palette__results" id="command-palette-results" role="listbox" ref={listRef}>
        {results.length === 0 ? (
          <li className="command-palette__empty">No encontramos nada para «{query}».</li>
        ) : (
          results.map((item, index) => {
            const Icon = item.icon
            const header = item.group !== lastGroup ? item.group : null
            lastGroup = item.group
            return (
              <li key={item.id} role="presentation">
                {header ? <p className="command-palette__group">{header}</p> : null}
                <div
                  id={`command-${item.id}`}
                  className={`command-palette__item ${index === current ? 'is-active' : ''}`}
                  role="option"
                  aria-selected={index === current}
                  data-index={index}
                  onMouseMove={() => setActive(index)}
                  onClick={() => run(item)}
                >
                  <span className="command-palette__icon" aria-hidden="true">
                    <Icon size={17} />
                  </span>
                  <span className="command-palette__text">
                    <strong>{item.label}</strong>
                    <small>{item.description}</small>
                  </span>
                  {index === current ? <CornerDownLeft className="command-palette__enter" size={15} aria-hidden="true" /> : null}
                </div>
              </li>
            )
          })
        )}
      </ul>
      <footer className="command-palette__footer">
        <span>
          <kbd>↑</kbd>
          <kbd>↓</kbd> para moverte
        </span>
        <span>
          <kbd>Enter</kbd> para abrir
        </span>
      </footer>
    </div>
  )
}
