# Diagrama del Proyecto — Sistema de Bloqueo de Distracciones Digitales para Estudiantes

**Focus Manager**

Manuela Riascos Hurtado
Institución Universitaria Antonio José Camacho

---

## 1. ¿Cómo funciona la solución?

Focus Manager es una **aplicación de escritorio para Windows** que el estudiante activa
antes de empezar a estudiar. Al activar un modo de concentración, el programa hace tres
cosas de forma automática y continua:

1. **Cierra y bloquea aplicaciones distractoras** (Discord, Telegram, Spotify, TikTok,
   juegos, etc.) revisando los procesos del sistema operativo.
2. **Restringe el navegador** para que solo permita los sitios académicos autorizados,
   cerrando cualquier pestaña que no esté en la lista blanca.
3. **Controla el tiempo** mediante un temporizador o técnica Pomodoro, y **protege la
   salida con un PIN** para que el estudiante no pueda desactivar el bloqueo antes de
   tiempo.

Mientras el modo está activo, un **monitor en segundo plano** (un hilo de ejecución
independiente) revisa cada pocos segundos los procesos abiertos y las pestañas del
navegador, aplicando las reglas una y otra vez hasta que el tiempo termina o se ingresa
el PIN correcto.

### Diagrama general de la arquitectura

```mermaid
flowchart TD
    U([👨‍🎓 Estudiante]) -->|abre y configura| GUI

    subgraph APP["💻 Focus Manager (aplicación de escritorio)"]
        GUI["🖥️ Interfaz Gráfica<br/>(PySide6 / Qt6)"]
        CFG["⚙️ Gestor de Configuración<br/>modos focus / ultra_focus"]
        PIN["🔐 Gestor de PIN<br/>(SHA-256)"]
        TIMER["⏱️ Temporizador<br/>Pomodoro / Sesión"]

        subgraph CTRL["🧠 Núcleo de control"]
            PROC["📋 Gestor de Procesos<br/>(psutil)"]
            BROWSER["🌐 Control de Navegador<br/>(Chrome DevTools)"]
            MON["🔁 Monitor en segundo plano<br/>(hilo cada ~10 s)"]
        end

        STATS["📊 Estadísticas<br/>(SQLite)"]
    end

    GUI --> CFG
    GUI --> PIN
    GUI --> TIMER
    GUI --> CTRL

    MON --> PROC
    MON --> BROWSER

    PROC -->|cierra apps no permitidas| OS["🪟 Sistema Operativo Windows"]
    BROWSER -->|cierra pestañas no autorizadas| CHROME["🌐 Chrome / Brave / Edge"]
    CTRL --> STATS

    PIN -.->|valida salida| GUI
    TIMER -.->|tiempo agotado: desactiva| GUI
```

### Diagrama de flujo de una sesión de estudio

```mermaid
flowchart TD
    A([Inicio]) --> B[El estudiante abre Focus Manager]
    B --> C{¿Qué modo elige?}
    C -->|Focus| D[Lista blanca de apps permitidas]
    C -->|Ultra Focus| E[Bloqueo total: 1 dominio + cierre de apps no permitidas]
    D --> F[Define duración / Pomodoro y PIN]
    E --> F
    F --> G[ACTIVAR modo]

    G --> H[[Monitor en segundo plano activo]]
    H --> I{¿Hay app distractora abierta?}
    I -->|Sí| J[Cierra el proceso con psutil]
    I -->|No| K{¿Pestaña no autorizada?}
    J --> K
    K -->|Sí| L[Cierra la pestaña vía Chrome DevTools]
    K -->|No| M{¿Tiempo agotado?}
    L --> M
    M -->|No| H
    M -->|Sí| N[Desactiva el modo automáticamente]

    H --> O{¿El estudiante intenta salir?}
    O -->|Sí| P{¿PIN correcto?}
    P -->|No| H
    P -->|Sí| N
    N --> Q[Guarda estadísticas en SQLite]
    Q --> R([Fin de la sesión])
```

---

## 2. ¿Qué tecnología utiliza?

El proyecto está desarrollado en **Python** y funciona sobre **Windows 10/11**.

| Componente | Tecnología | ¿Para qué sirve? |
|---|---|---|
| Lenguaje | **Python 3.8+** | Lenguaje principal del proyecto |
| Interfaz gráfica | **PySide6 (Qt6)** | Ventanas, botones y diseño de la aplicación |
| Gestión de procesos | **psutil** | Detectar y cerrar las aplicaciones distractoras |
| Control del navegador | **Chrome DevTools Protocol** (vía `requests` y `websocket-client`) | Cerrar pestañas no autorizadas en Chrome / Brave / Edge |
| Seguridad / PIN | **hashlib (SHA-256)** | Guardar el PIN cifrado (control parental) |
| Estadísticas | **SQLite** | Registrar tiempo de estudio, sesiones y apps cerradas |
| Concurrencia | **threading** | Monitor en segundo plano sin congelar la interfaz |
| Bandeja del sistema | **pystray + Pillow** | Mantener la app accesible desde el ícono del reloj |
| Integración Windows | **pywin32** | Funciones específicas del sistema operativo |
| Empaquetado | **PyInstaller** | Generar el ejecutable `.exe` distribuible |

### Diagrama de componentes y tecnologías

```mermaid
graph LR
    subgraph PY["🐍 Python 3.8+ — Windows 10/11"]
        direction TB
        UI["PySide6 / Qt6<br/>👉 Interfaz gráfica"]
        PS["psutil<br/>👉 Control de procesos"]
        CDP["Chrome DevTools<br/>requests + websocket-client<br/>👉 Control del navegador"]
        HASH["hashlib SHA-256<br/>👉 Seguridad del PIN"]
        DB["SQLite<br/>👉 Estadísticas"]
        TH["threading<br/>👉 Monitor en 2.º plano"]
        TRAY["pystray + Pillow<br/>👉 Bandeja del sistema"]
        PKG["PyInstaller<br/>👉 Genera el .exe"]
    end

    UI --- PS
    UI --- CDP
    UI --- HASH
    UI --- DB
    PS --- TH
    CDP --- TH
```

---

## Cómo convertir estos diagramas en imágenes para el documento

Los diagramas están escritos en **Mermaid**. Para insertarlos en Word como imagen:

1. Entra a <https://mermaid.live>
2. Copia y pega el contenido de un bloque ` ```mermaid ` (sin las comillas).
3. Usa **Actions → PNG / SVG** para descargar la imagen.
4. Inserta la imagen en tu documento de Word.

> También se ven directamente en VS Code (con la extensión *Markdown Preview Mermaid*) y
> en GitHub sin instalar nada.
