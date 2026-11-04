import { useEffect, useRef } from 'react'
import JsBarcode from 'jsbarcode'

interface PackageBarcodeProps {
  value: string
}

export function PackageBarcode({ value }: PackageBarcodeProps) {
  const barcodeRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    if (!barcodeRef.current) return

    JsBarcode(barcodeRef.current, value, {
      format: 'CODE128',
      width: 2,
      height: 72,
      margin: 8,
      displayValue: true,
      font: 'ui-monospace, SFMono-Regular, Consolas, monospace',
      fontSize: 16,
      textMargin: 7,
      background: '#ffffff',
      lineColor: '#000000',
    })
  }, [value])

  return (
    <svg
      className="package-barcode"
      ref={barcodeRef}
      role="img"
      aria-label={`Código de barras del paquete ${value}`}
    />
  )
}
