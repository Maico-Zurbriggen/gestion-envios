# Identidad visual

## Paleta

- Primario: índigo `#4F46E5`.
- Secundario: índigo claro `#818CF8`.
- Acento: ámbar `#F59E0B`.
- Neutros: escala fría basada en slate.

Las escalas completas, colores semánticos y tokens de interfaz están definidos en `front/src/styles/theme.css`. Los componentes deben consumir variables semánticas como `--color-primary`, `--color-text` o `--color-border` antes que tonos concretos.

## Criterios de interfaz

- Superficies claras, bordes suaves y elevación moderada.
- Índigo para acciones principales, navegación y foco.
- Ámbar para énfasis puntual y advertencias, no para acciones primarias.
- Jerarquía tipográfica clara y textos secundarios en grises fríos.
- Estados de foco visibles, contraste suficiente y diseño responsive desde 320 px.
- Los iconos de interfaz provienen de `lucide-react`. Se priorizan en botones y acciones cuando ayuden a reconocer su función, siempre con nombre accesible cuando el icono no esté acompañado por texto.
