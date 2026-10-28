# Identidad visual

La web comparte la identidad de las presentaciones (Sprint Reviews) y de los informes del proyecto: misma tipografía, misma paleta y los mismos recursos visuales.

## Tipografía

- Montserrat (300 a 700), cargada desde Google Fonts en `front/index.html`.
- Títulos en SemiBold (600); cuerpo en Regular (400); etiquetas superiores en SemiBold, mayúsculas y espaciadas.

## Paleta

- Texto y títulos: azul petróleo `#0F2A37` (escala `--color-neutral-*`).
- Marca y acciones: naranja `#D9701F` (`--color-primary-500`, `--color-brand`). Los botones principales usan `#B85C17` (`--color-primary`), la variante accesible con texto blanco (contraste ≥ 4,5:1).
- Completado y confirmaciones: verde azulado `#138A80` (`--color-success`, escala `--color-teal-*`). Los enlaces usan su variante `#0F766E` (`--color-link`).
- Advertencias: dorado `#B7791F` (`--color-warning`, escala `--color-accent-*`).
- Fondo `#F7F9FA` con el degradé suave naranja y verde azulado de las diapositivas (`--page-glow`); superficies blancas con borde `#DCE4E8`.

Las escalas completas y los tokens están en `front/src/styles/theme.css`. Los componentes deben consumir variables semánticas (`--color-primary`, `--color-text`, `--color-border`, `--shadow-card`…) antes que tonos concretos.

## Componentes compartidos

- `front/src/styles/base.css`: estilos de los elementos HTML (títulos, enlaces, foco, selección, movimiento reducido).
- `front/src/styles/ui.css`: etiqueta superior (`.eyebrow`), botones (`.btn`), tarjetas (`.surface-card`), insignias (`.badge`), entrada animada de cada pantalla y estilos del modal.
- `front/src/shared/components/Modal.tsx`: modal accesible sobre `<dialog>` (foco atrapado, Escape, fondo inerte). En pantallas de hasta 560 px se abre desde abajo como hoja.

## Criterios de interfaz

- Cada pantalla abre con etiqueta superior naranja, título y descripción breve, alineados a la izquierda en el mismo contenedor.
- Tarjetas blancas con borde suave y sombra moderada (`--shadow-card`), como en las presentaciones.
- Naranja para acciones principales, ítem activo del menú y foco; verde azulado para estados completados; dorado para advertencias.
- Los detalles, formularios secundarios y confirmaciones se abren en modales en lugar de paneles desplegables. Se mantienen en la página las operaciones que no deben interrumpirse (por ejemplo, registrar una entrega mientras hay un reintento pendiente).
- Menú lateral azul petróleo con la marca en naranja; en pantallas angostas se abre como panel deslizable.
- Animaciones breves (160 a 420 ms) para entrada de pantallas, modales y respuesta de botones; se desactivan con `prefers-reduced-motion`.
- Estados de foco visibles, contraste suficiente y diseño responsive desde 320 px.
- Los iconos de interfaz provienen de `lucide-react`. Se priorizan en botones y acciones cuando ayuden a reconocer su función, siempre con nombre accesible cuando el icono no esté acompañado por texto.
- La aplicación admite temas claro y oscuro mediante `data-theme` en el elemento raíz. La preferencia se guarda localmente y los componentes deben utilizar tokens semánticos para funcionar correctamente en ambos temas.
