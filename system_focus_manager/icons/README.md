# Cómo usar iconos en vez de emojis

Esta carpeta es para guardar tus archivos de iconos (.png, .svg, .ico).

## Dónde conseguir iconos gratis:

1. **Flaticon** (https://www.flaticon.com/)
   - Miles de iconos gratis
   - Descarga en PNG o SVG
   - Busca "focus", "timer", "productivity"

2. **Material Icons** (https://fonts.google.com/icons)
   - Iconos de Google
   - Descarga SVG gratis
   - Estilo minimalista

3. **Feather Icons** (https://feathericons.com/)
   - Iconos minimalistas
   - SVG gratis
   - Muy limpio y profesional

## Cómo implementar los iconos:

### Opción 1: Archivos de iconos locales

1. Guarda tus iconos aquí (ej: `focus.png`, `timer.png`, `creative.png`)
2. Edita `gui.py` línea ~497:

```python
# Antes (con emoji):
btn = QPushButton(f"{mode_data['icon']}\n{mode_data['name']}")

# Después (con icono):
from PySide6.QtGui import QIcon
icon_path = Path(__file__).parent / 'icons' / f"{mode_id}.png"
btn = QPushButton(mode_data['name'])
if icon_path.exists():
    btn.setIcon(QIcon(str(icon_path)))
    btn.setIconSize(QSize(48, 48))
```

3. Edita cada archivo en `modes/` (ej: `focus.json`):
```json
{
  "name": "Focus",
  "icon": "focus.png",  // nombre del archivo
  ...
}
```

### Opción 2: Usar solo texto

```python
btn = QPushButton(mode_data['name'])  // Sin icono, solo texto
```

### Tamaños recomendados:
- **PNG**: 64x64 píxeles o 128x128
- **SVG**: Cualquier tamaño (escalable)

### Colores recomendados:
- Iconos monocromáticos (blanco o negro)
- O usa iconos con los colores de tu tema (#3498db, #27ae60, etc.)

## Ejemplo completo:

Si descargas `focus-icon.png` de Flaticon:
1. Renómbralo a `focus.png`
2. Guárdalo en esta carpeta `icons/`
3. Modifica `gui.py` como se explicó arriba
4. Los iconos se cargarán automáticamente
