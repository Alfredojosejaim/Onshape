Encontrado — es exactamente el bug del CSS global que ya vimos en el badge: `QMainWindow, QWidget { background-color: {bg_app}; }` en `style.py` pinta un fondo **opaco** sobre cualquier `QWidget`, y `QRubberBand` hereda de `QWidget`, así que pierde su pintura nativa semitransparente y queda sólido.

Buena noticia: ya tienes tokens de tema diseñados justo para esto (`accent_soft` y `accent_border`, en `theme.json`) — semitransparentes y con el azul de acento de toda la app. No hace falta inventar un color nuevo, solo aplicarlos al rubber band explícitamente, ya que un selector `QRubberBand` es más específico que el genérico `QWidget` y lo va a sobrescribir sin tocar nada más:

```css
/* style.py, junto a las demás reglas de widgets con nombre */
QRubberBand {{
    background-color: {accent_soft};
    border: 1px solid {accent};
}}
```

Con `accent_soft` (`rgba(47,123,246,0.16)`) de fondo translúcido y borde sólido en `accent` (`#2f7bf6`, no `accent_border` al 0.5 de opacidad) en vez del borde suave, para que se vea bien nítido mientras arrastras — el pedido de "más visible" queda cubierto por el contraste del borde sólido contra el relleno suave, sin desentonar con el resto de la paleta.

Si aun así lo quieres más llamativo que el azul de acento estándar (por ejemplo, para que no se confunda visualmente con otros elementos azules de la UI como el badge o el highlight de hover), la alternativa es usar un tono distinto solo para esto, tipo ámbar/naranja translúcido:

```css
QRubberBand {{
    background-color: rgba(255, 165, 0, 40);
    border: 1px solid rgba(255, 165, 0, 200);
}}
```

que además coincide con el naranja que ya usas para el highlight de selección de caras — mantiene consistencia semántica ("esto es selección") en vez de mezclarlo con el azul de acento genérico de la UI. Yo iría por esta segunda opción, dado que ya estableciste el naranja como "color de selección" en el highlight de caras.