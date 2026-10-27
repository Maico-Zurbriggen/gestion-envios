import { useEffect, useRef, useState, type PointerEvent } from 'react'
import { Eraser } from 'lucide-react'
import './SignaturePad.css'

export function SignaturePad({ onChange, disabled }: { onChange: (value: string) => void; disabled: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const drawing = useRef<number | null>(null)
  const uploadVersion = useRef(0)
  const [error, setError] = useState('')
  function clearCanvas() {
    const canvas = canvasRef.current
    const context = canvas?.getContext('2d')
    if (!canvas || !context) return
    context.fillStyle = getComputedStyle(canvas).backgroundColor
    context.fillRect(0, 0, canvas.width, canvas.height)
  }
  useEffect(() => {
    const canvas = canvasRef.current
    const context = canvas?.getContext('2d')
    if (canvas && context) { context.fillStyle = getComputedStyle(canvas).backgroundColor; context.fillRect(0, 0, canvas.width, canvas.height) }
    return () => { uploadVersion.current += 1 }
  }, [])
  function point(event: PointerEvent<HTMLCanvasElement>) {
    const canvas = event.currentTarget
    const rect = canvas.getBoundingClientRect()
    return [(event.clientX - rect.left) * canvas.width / rect.width, (event.clientY - rect.top) * canvas.height / rect.height] as const
  }
  function down(event: PointerEvent<HTMLCanvasElement>) {
    if (disabled || drawing.current !== null) return
    uploadVersion.current += 1
    setError('')
    const context = event.currentTarget.getContext('2d')
    if (!context) return
    drawing.current = event.pointerId
    event.currentTarget.setPointerCapture(event.pointerId)
    const [x, y] = point(event)
    context.strokeStyle = getComputedStyle(event.currentTarget).color
    context.lineWidth = 3; context.lineCap = 'round'; context.lineJoin = 'round'
    context.beginPath(); context.moveTo(x, y); context.lineTo(x + .1, y + .1); context.stroke()
    onChange('')
  }
  function move(event: PointerEvent<HTMLCanvasElement>) {
    if (disabled || drawing.current !== event.pointerId) return
    const context = event.currentTarget.getContext('2d')
    const [x, y] = point(event)
    context?.lineTo(x, y); context?.stroke()
  }
  function up(event: PointerEvent<HTMLCanvasElement>) {
    if (drawing.current !== event.pointerId) return
    drawing.current = null
    onChange(event.currentTarget.toDataURL('image/png').split(',')[1])
  }
  async function upload(file: File | undefined) {
    if (!file) return
    const version = ++uploadVersion.current
    setError(''); onChange('')
    if (file.type !== 'image/png' || file.size > 256 * 1024) { setError('Elegí una firma PNG de hasta 256 KiB y 1024 × 1024 píxeles.'); return }
    const url = URL.createObjectURL(file)
    try {
      const image = new Image(); image.src = url; await image.decode()
      if (version !== uploadVersion.current) return
      if (image.width > 1024 || image.height > 1024) throw new Error('dimensions')
      clearCanvas()
      const canvas = canvasRef.current!
      const scale = Math.min(canvas.width / image.width, canvas.height / image.height)
      canvas.getContext('2d')?.drawImage(image, 0, 0, image.width * scale, image.height * scale)
      onChange(canvas.toDataURL('image/png').split(',')[1])
    } catch { if (version === uploadVersion.current) setError('No pudimos leer la firma. Usá un PNG válido de hasta 1024 × 1024 píxeles.') }
    finally { URL.revokeObjectURL(url) }
  }
  return <div className="ops-stack">
    <p id="signature-instructions">Firma del receptor: dibujá con el dedo o el mouse. También podés adjuntar su firma en PNG.</p>
    <canvas ref={canvasRef} className="signature-pad" width={720} height={240} onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up} role="img" aria-label="Área para dibujar la firma del receptor" aria-describedby="signature-instructions" />
    <button className="ops-button" type="button" disabled={disabled} onClick={() => { uploadVersion.current += 1; clearCanvas(); setError(''); onChange('') }}><Eraser size={18} aria-hidden="true" /> Limpiar firma</button>
    <label className="form-field" htmlFor="signature-file">Adjuntar firma PNG (alternativa al dibujo)<input id="signature-file" type="file" accept="image/png" disabled={disabled} onChange={(event) => { void upload(event.target.files?.[0]); event.target.value = '' }} /></label>
    {error && <p className="form-error" role="alert">{error}</p>}
  </div>
}
