# 📤 INSTRUCCIONES PARA SUBIR A GITHUB

## ✅ LO QUE YA ESTÁ HECHO:

1. ✅ Comillas removidas de "Complete productivity tool"
2. ✅ Traducciones completadas (Timer, Auditory, diálogos)
3. ✅ Sistema de protección de copyright implementado:
   - `_watermark.py` - Verificación de marca de agua
   - Encabezados de copyright en archivos principales
   - Archivo `NOTICE` con información legal
   - Copyright en `main.py` que se muestra al iniciar
4. ✅ README.md con secciones para videos
5. ✅ Git inicializado y primer commit hecho
6. ✅ Screenshots agregados en `system_focus_manager/docs/screenshots/`

---

## 📤 PASOS PARA SUBIR A GITHUB:

### 1. Crear repositorio en GitHub

1. Ve a: https://github.com/new
2. **Repository name**: `focus-manager`
3. **Description**: `Complete productivity tool to maintain focus and block distractions on Windows`
4. **Visibility**: Public
5. **NO** marques "Initialize with README" (ya tienes uno)
6. Click "Create repository"

### 2. Conectar y subir

Abre la terminal en `c:\Users\manhu\Desktop\manager` y ejecuta:

```bash
# Conectar con GitHub (reemplaza con tu URL)
git remote add origin https://github.com/Elah2022/focus-manager.git

# Subir el código
git branch -M main
git push -u origin main
```

Si te pide autenticación:
- Usuario: `Elah2022`
- Password: usa un **Personal Access Token** (no tu password normal)

Para crear un token:
1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token → Marca "repo" → Generate
3. Copia el token y úsalo como password

---

## 🎬 AGREGAR TUS VIDEOS:

### Opción 1: Subir videos a YouTube (RECOMENDADO)

1. Sube tus videos a tu canal de YouTube
2. Obtén los enlaces
3. Edita `README.md` y reemplaza `LINK_A_TU_VIDEO_AQUI` con tus URLs

Ejemplo en `README.md` línea 48:
```markdown
> **Video Tutorial**: [Watch on YouTube](https://youtube.com/watch?v=TU_VIDEO_ID)
```

### Opción 2: Usar GIFs (para demos cortos)

1. Convierte tus videos a GIF (usa https://ezgif.com/)
2. Guarda los GIFs en: `system_focus_manager/docs/demos/`
3. Ya están referenciados en el README:
   - `docs/demos/focus-mode-demo.gif`
   - `docs/demos/ultra-focus-demo.gif`

### Opción 3: Usar GitHub Releases

1. Ve a tu repositorio en GitHub
2. Releases → Create a new release
3. Tag: `v2.0`
4. Title: `System Focus Manager v2.0`
5. Attach files: sube tus videos (.mp4)
6. Publish release

---

## 📸 TUS SCREENSHOTS YA ESTÁN INCLUIDOS:

Los screenshots están en:
```
system_focus_manager/docs/screenshots/
├── image1.png
├── image2.png
├── image3.png
├── image5.png
├── image6.png
├── image7.png
└── image8.png
```

Para que se vean en el README, renómbralos así:
```bash
cd system_focus_manager/docs/screenshots
mv image1.png main-interface.png
mv image2.png focus-mode.png
mv image3.png ultra-focus.png
mv image5.png statistics.png
```

Luego:
```bash
git add .
git commit -m "Rename screenshots for README"
git push
```

---

## 🛡️ PROTECCIÓN DE COPYRIGHT IMPLEMENTADA:

Tu código ahora tiene múltiples capas de protección:

### 1. Marca de Agua en el Código (`_watermark.py`)
- Se verifica al iniciar la aplicación
- Contiene información codificada
- Si alguien lo elimina, se muestra advertencia

### 2. Encabezados de Copyright
Todos los archivos principales tienen:
```python
"""
Copyright © 2025 Manuela Riascos Hurtado
Original Author: Manuela Riascos Hurtado
Email: manhurta54@gmail.com
...
"""
```

### 3. Archivo NOTICE
- Información legal completa
- Requisitos de atribución
- Acciones prohibidas
- Contacto para uso comercial

### 4. Mensaje al Iniciar
Al ejecutar `python main.py` se muestra:
```
System Focus Manager v2.0
© Copyright © 2025 Manuela Riascos Hurtado
Author: Manuela Riascos Hurtado
GitHub: https://github.com/Elah2022/focus-manager
```

### 5. Diálogo "About"
Muestra tu información de contacto y copyright

---

## ⚠️ IMPORTANTE - VERIFICAR ANTES DE SUBIR:

1. ✅ Verifica que no haya información personal en screenshots
2. ✅ Asegúrate de que los logs están en .gitignore
3. ✅ Verifica que la base de datos (*.db) no se suba
4. ✅ Confirma que el PIN no está visible en ningún lado

Archivos protegidos por .gitignore:
- `*.log` - Logs
- `*.db` - Base de datos
- `pin_hash.txt` - PIN encriptado
- `data/` - Datos personales
- `__pycache__/` - Cache de Python

---

## 🎉 DESPUÉS DE SUBIR:

1. **Configura GitHub Pages** (opcional):
   - Settings → Pages → Source: main branch
   - Esto crea una página web de tu proyecto

2. **Agrega topics**:
   - En tu repo → About (rueda) → Topics
   - Agrega: `productivity`, `focus`, `windows`, `python`, `pyqt`

3. **Crea un Release**:
   - Releases → Create new release
   - Tag: `v2.0`
   - Title: `System Focus Manager v2.0 - Initial Release`
   - Describe las características
   - Attach el ejecutable (.exe) si lo compilas

---

## 📧 CONTACTO Y SOPORTE:

Si alguien quiere usar tu código comercialmente:
- Email: manhurta54@gmail.com
- Puedes cobrar por licencias comerciales
- Puedes ofrecer consultoría/personalización

---

## ✨ COMANDO FINAL PARA SUBIR:

```bash
cd c:\Users\manhu\Desktop\manager

# Agregar remote (solo primera vez)
git remote add origin https://github.com/Elah2022/focus-manager.git

# Subir
git push -u origin main
```

¡LISTO! Tu código está protegido y listo para compartir 🚀
