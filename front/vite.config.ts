import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'
import basicSsl from '@vitejs/plugin-basic-ssl'
import { defineConfig } from 'vite'

// La cámara del celular solo funciona en un contexto seguro. Con `HTTPS_DEV=true`
// el servidor de desarrollo usa un certificado autofirmado para probar el
// escáner entrando por la IP de la red local (el navegador pide aceptarlo).
const httpsDev = process.env.HTTPS_DEV === 'true'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    babel({ presets: [reactCompilerPreset()] }),
    ...(httpsDev ? [basicSsl()] : []),
  ],
  server: {
    // Solo con HTTPS_DEV escucha en la red local, para abrir la app desde el celular.
    host: httpsDev ? true : undefined,
  },
})
