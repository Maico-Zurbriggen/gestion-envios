import { useState, type FormEvent } from 'react'
import { PackageSearch, Search } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { ScanWithCameraButton } from '../../../shared/components/ScanWithCameraButton'
import { PACKAGE_CODE_PATTERN } from '../../../shared/services/scannedCode'

/** «Ir a un paquete»: escribir o escanear el número y abrir su trazabilidad. */
export function PackageSearchBar({ initialCode = '', autoFocus = false }: { initialCode?: string; autoFocus?: boolean }) {
  const navigate = useNavigate()
  const [code, setCode] = useState(initialCode)

  function open(value: string) {
    const normalized = value.replace(/\s+/g, '').toUpperCase()
    if (normalized) navigate(`/monitor/trazabilidad/${normalized}`)
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    open(code)
  }

  return (
    <form className="trace-search" onSubmit={handleSubmit} role="search" aria-label="Ir a un paquete">
      <div className="list-search">
        <Search size={16} aria-hidden="true" />
        <label className="visually-hidden" htmlFor="trace-code">Número de paquete</label>
        <input
          id="trace-code"
          placeholder="Ir a un paquete: PAQ-XXXXXXXXXX"
          value={code}
          onChange={(event) => setCode(event.target.value)}
          autoComplete="off"
          spellCheck={false}
          autoFocus={autoFocus}
        />
      </div>
      <button className="btn btn--primary" type="submit" disabled={!code.trim()}>
        <PackageSearch size={17} aria-hidden="true" />
        Ver trazabilidad
      </button>
      <ScanWithCameraButton
        mode="single"
        className="btn"
        pattern={PACKAGE_CODE_PATTERN}
        patternMessage={(read) => `${read} no es un número de paquete (PAQ-XXXXXXXXXX).`}
        onScan={(read) => {
          setCode(read)
          open(read)
        }}
      />
    </form>
  )
}
