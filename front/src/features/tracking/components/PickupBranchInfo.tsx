import { Building2, CircleCheck, Clock3, IdCard, LoaderCircle, RefreshCw } from 'lucide-react'
import { usePickupOptions } from '../hooks/useShipmentTracking'

interface PickupBranchInfoProps {
  token: string
  statusKey: string
}

export function PickupBranchInfo({ token, statusKey }: PickupBranchInfoProps) {
  const options = usePickupOptions(token, true, statusKey)

  if (options.isPending) {
    return <p className="tracking-pickup" role="status"><LoaderCircle className="loading-icon" size={17} aria-hidden="true" /> Consultando la sucursal de retiro…</p>
  }
  if (options.isError) {
    return (
      <div className="tracking-pickup" role="alert">
        <p>{options.error.message}</p>
        <button type="button" onClick={() => void options.refetch()}><RefreshCw size={17} aria-hidden="true" /> Reintentar</button>
      </div>
    )
  }

  const { data } = options
  if (!data.applies) return null
  const readyCount = data.packages.filter((item) => item.ready).length

  return (
    <section className="tracking-pickup" aria-labelledby="tracking-pickup-title">
      <h3 id="tracking-pickup-title"><Building2 size={20} aria-hidden="true" /> Retiro en sucursal</h3>
      {data.branch
        ? <p><strong>{data.branch.name}</strong> · {data.branch.address}, {data.branch.city}, {data.branch.province}</p>
        : <p>El envío no tiene una sucursal de retiro asignada. Consultá en la sucursal más cercana.</p>}
      {readyCount === data.packages.length && readyCount > 0
        ? <p className="tracking-pickup__ready"><CircleCheck size={17} aria-hidden="true" /> Ya podés pasar a retirar {readyCount === 1 ? 'el paquete' : 'los paquetes'}.</p>
        : readyCount > 0
          ? <p className="tracking-pickup__ready"><CircleCheck size={17} aria-hidden="true" /> {readyCount} de {data.packages.length} paquetes ya están disponibles para retirar.</p>
          : <p><Clock3 size={17} aria-hidden="true" /> Todavía no está disponible para retirar. Cuando llegue a la sucursal lo vas a ver en este seguimiento.</p>}
      <div>
        <p><IdCard size={17} aria-hidden="true" /> <strong>Qué llevar</strong></p>
        <ul>
          <li>Destinatario: {data.requirements.recipient}</li>
          <li>Otra persona: {data.requirements.authorizedPerson}</li>
        </ul>
      </div>
    </section>
  )
}
