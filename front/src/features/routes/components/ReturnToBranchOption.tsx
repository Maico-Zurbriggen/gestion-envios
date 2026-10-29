import { Undo2 } from 'lucide-react'

/** Casilla «Volver a la sucursal al terminar», con la explicación de cómo se ve en el mapa. */
export function ReturnToBranchOption({ id, checked, onChange, disabled }: {
  id: string
  checked: boolean
  onChange: (checked: boolean) => void
  disabled?: boolean
}) {
  return <label className="route-check route-return-option" htmlFor={id}>
    <input id={id} type="checkbox" checked={checked} disabled={disabled} onChange={(event) => onChange(event.target.checked)} aria-describedby={`${id}-help`} />
    <span>
      <strong><Undo2 size={15} aria-hidden="true" /> Volver a la sucursal al terminar</strong>
      <small id={`${id}-help`}>{checked
        ? 'El orden tiene en cuenta el regreso. En el mapa, la vuelta se ve en azul y punteada.'
        : 'El recorrido termina en la última parada, sin tramo de regreso.'}</small>
    </span>
  </label>
}
