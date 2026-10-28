# Gestión de envíos · frontend

React, TypeScript y Vite. Las decisiones de arquitectura y diseño están en [`knowledge/`](../knowledge/README.md).

## Comandos

| Comando | Uso |
|---|---|
| `npm run dev` | Servidor de desarrollo. La API se toma de `VITE_API_URL`. |
| `npm run lint` | ESLint. |
| `npm run build` | Chequeo de tipos y build de producción. |
| `npm test` | Reglas puras (seguimiento, entrega, escáner y etiquetas). |
| `npm run test:browser` | Recorrido de los sprints en el navegador. Requiere Vite en 5173 y Chrome con CDP en 9227. |
| `npm run test:navigation` | Navegación del panel con y sin sesión. Mismos requisitos. |

Antes de entregar cambios, correr `npm run lint` y `npm run build`.
