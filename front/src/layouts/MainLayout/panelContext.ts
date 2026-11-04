import { createContext, useContext } from 'react'

/** `true` cuando la página se muestra dentro del panel (con el menú lateral). */
export const PanelLayoutContext = createContext(false)

export function useInsidePanel() {
  return useContext(PanelLayoutContext)
}
