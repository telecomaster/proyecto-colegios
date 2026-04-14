# Proyecto Colegios — Virtual Lab Assistant
## Documentación Técnica del Proyecto

---

## ¿Qué es este proyecto?

Es un **asistente de laboratorio virtual con inteligencia artificial** pensado para estudiantes de ingeniería. En lugar de dar respuestas directas, el sistema guía al estudiante con preguntas socráticamente diseñadas para que llegue a la solución por sí mismo.

El sistema está especializado en tres dominios:

| Agente | Dominio |
|---|---|
| **VHDL/Verilog Agent** | Diseño digital, circuitos sincrónicos, simulación |
| **RF Signal Analysis Agent** | Modulación, espectro, antenas |
| **Network Protocol Agent** | TCP/IP, enrutamiento OSPF/RIP, VLANs |

---

## Arquitectura del sistema

```
[ Navegador (puerto 3000) ]
         │
         ▼
[ nginx — sirve el frontend ]
   frontend/index.html
         │  (llamadas REST a localhost:8000)
         ▼
[ Docker: Orchestrator FastAPI (puerto 8000) ]
   ├── router.py     → Semantic Routing (sentence-transformers + coseno)
   ├── rag.py        → RAG con FAISS (busca en knowledge_base/)
   └── main.py       → Orquesta todo y llama al LLM
         │
         ▼
[ Ollama — corre NATIVO en Windows (puerto 11434) ]
   modelo: llama3.1:8b  (usa GPU si está disponible)
```

**¿Por qué Ollama corre fuera de Docker?**
Para aprovechar la GPU (RTX 3060). Docker en Windows no puede acceder directamente a la GPU NVIDIA. El contenedor se comunica con Ollama a través de `host.docker.internal:11434`.

### Flujo de una consulta

1. El usuario escribe una pregunta en el chat.
2. **Semantic Router** (`router.py`): convierte la pregunta en un vector (embedding) y lo compara por similitud coseno con centroides de cada dominio. Determina qué agente responde.
3. **RAG** (`rag.py`): busca en la base de conocimiento (`knowledge_base/*.md`) los 3 fragmentos más relevantes usando FAISS.
4. **LLM** (`main.py`): envía la pregunta + contexto recuperado a Ollama con un prompt socrático estricto. El modelo genera 1-2 oraciones y una pregunta guía, sin revelar la respuesta.
5. El frontend muestra la respuesta y visualiza el pipeline interno (scores de routing, chunks recuperados, pasos ejecutados).

---

## Archivos del proyecto

```
proyecto_colegios/
├── docker-compose.yml                  # Define los dos servicios (orchestrator + frontend)
├── start_demo.bat                      # Script para arrancar todo en Windows
├── stop_demo.bat                       # Script para detener todo
├── frontend/
│   └── index.html                      # UI completa (HTML + CSS + JS, todo en un archivo)
└── orchestrator/
    ├── Dockerfile                      # Imagen Docker del backend
    ├── requirements.txt                # Dependencias Python
    ├── main.py                         # FastAPI: endpoints /health, /query, /ollama-status
    ├── router.py                       # Enrutador semántico (sentence-transformers)
    ├── rag.py                          # Pipeline RAG con FAISS
    └── knowledge_base/
        └── vhdl_guide.md               # Base de conocimiento (formato Markdown)
```

### ¿Qué hace cada archivo Python?

- **`main.py`**: Punto de entrada. Define los endpoints REST. Orquesta router → RAG → LLM. Incluye el prompt socrático.
- **`router.py`**: Carga el modelo `all-MiniLM-L6-v2` de sentence-transformers. Construye centroides por dominio con keywords. Clasifica consultas por similitud coseno.
- **`rag.py`**: Lee los `.md` de `knowledge_base/`, los divide en chunks de 300 caracteres con overlap de 50, construye un índice FAISS en memoria al arrancar, y recupera los top-K más similares a cada consulta.

### Dependencias Python (requirements.txt)

```
fastapi==0.111.0
uvicorn[standard]==0.30.1
faiss-cpu==1.8.0
sentence-transformers==3.0.1
numpy==1.26.4
httpx==0.27.0
python-multipart==0.0.9
```

---

## Requisitos para ejecutar el proyecto

### Software que debe estar instalado en la computadora

| Requisito | Versión mínima | Descarga |
|---|---|---|
| **Docker Desktop** | Cualquier versión reciente | https://www.docker.com/products/docker-desktop |
| **Ollama** | Cualquier versión reciente | https://ollama.com/download |

> No se necesita Python instalado localmente — el backend corre dentro de Docker.

### Recursos de hardware recomendados

- **RAM**: mínimo 8 GB (16 GB recomendado)
- **Disco**: ~5 GB libres (para la imagen Docker + el modelo LLM)
- **GPU**: opcional pero recomendado (NVIDIA). Sin GPU funciona igual, pero más lento.

---

## Pasos para ejecutar el proyecto

### Paso 1 — Instalar Docker Desktop

1. Descargar e instalar desde https://www.docker.com/products/docker-desktop
2. Abrir Docker Desktop y asegurarse de que esté corriendo (ícono en la barra de tareas).

### Paso 2 — Instalar Ollama

1. Descargar e instalar desde https://ollama.com/download
2. Ollama se instala como un servicio y corre automáticamente en segundo plano.

### Paso 3 — Descargar el modelo LLM

Abrir una terminal (CMD o PowerShell) y ejecutar:

```
ollama pull llama3.1:8b
```

> Este comando descarga el modelo (~4.7 GB). Solo se hace una vez.
>
> **Alternativa liviana** si la computadora tiene poca RAM o disco:
> ```
> ollama pull llama3.2:1b
> ```
> Si usan el modelo `1b`, también deben cambiar la línea `MODEL_NAME` en `orchestrator/main.py`:
> ```python
> MODEL_NAME = "llama3.2:1b"
> ```

### Paso 4 — Ajustar el script de inicio (IMPORTANTE)

El archivo `start_demo.bat` tiene una ruta de Ollama codificada para esta computadora:

```bat
set OLLAMA="C:\Users\renes\AppData\Local\Programs\Ollama\ollama.exe"
```

En otra computadora, esa ruta puede ser diferente. Hay dos opciones:

**Opción A** — Editar la línea para que apunte a donde está instalado Ollama en esa computadora.

**Opción B** — Ignorar el script `.bat` y ejecutar manualmente (ver Paso 5 alternativo).

### Paso 5 — Iniciar el sistema

**Con el script (Windows):**

Hacer doble clic en `start_demo.bat` o ejecutarlo desde CMD:
```
start_demo.bat
```

El script:
1. Verifica y descarga el modelo de Ollama.
2. Construye y levanta los contenedores Docker.
3. Espera 15 segundos y abre el navegador.

**Sin el script (manual):**

Abrir una terminal en la carpeta del proyecto y ejecutar:

```bash
docker compose up -d --build
```

Luego abrir el navegador en `http://localhost:3000`.

### Paso 6 — Usar el sistema

- Abrir: **http://localhost:3000** (interfaz de chat)
- API docs: **http://localhost:8000/docs** (documentación automática de FastAPI)
- Health check: **http://localhost:8000/health**

### Paso 7 — Detener el sistema

```
stop_demo.bat
```

O manualmente:
```bash
docker compose down
```

---

## Qué archivos enviar

Enviar **toda la carpeta del proyecto** comprimida en ZIP. Debe incluir:

```
proyecto_colegios.zip
├── docker-compose.yml          ✅ obligatorio
├── start_demo.bat              ✅ obligatorio (ajustar la ruta de Ollama)
├── stop_demo.bat               ✅ obligatorio
├── frontend/
│   └── index.html              ✅ obligatorio
└── orchestrator/
    ├── Dockerfile              ✅ obligatorio
    ├── requirements.txt        ✅ obligatorio
    ├── main.py                 ✅ obligatorio
    ├── router.py               ✅ obligatorio
    ├── rag.py                  ✅ obligatorio
    └── knowledge_base/
        └── vhdl_guide.md       ✅ obligatorio
```

**NO hace falta enviar:**
- Ningún entorno virtual de Python (`venv/`, `.venv/`)
- Imágenes Docker (se construyen automáticamente)
- El modelo LLM (se descarga con `ollama pull`)

---

## Cómo extender el proyecto

### Agregar un nuevo agente/dominio

1. Agregar keywords en `orchestrator/router.py` dentro del diccionario `DOMAIN_KEYWORDS`:
   ```python
   "nuevo_dominio": ["keyword1", "keyword2", ...]
   ```
2. Agregar el label en `DOMAIN_LABELS`:
   ```python
   "nuevo_dominio": "Nombre del Nuevo Agente"
   ```
3. Crear un archivo `.md` en `orchestrator/knowledge_base/` con el contenido para ese dominio.
4. Agregar el chip visual en `frontend/index.html`.

### Agregar más conocimiento a un dominio existente

Editar o agregar archivos `.md` en `orchestrator/knowledge_base/`. El RAG los carga automáticamente al arrancar el contenedor. Separar secciones con `\n---\n` para mejor chunking.

### Cambiar el modelo LLM

Editar `MODEL_NAME` en `orchestrator/main.py` y hacer `ollama pull <nuevo-modelo>` antes de iniciar.

---

## Solución de problemas frecuentes

| Problema | Causa probable | Solución |
|---|---|---|
| El frontend muestra "Offline" | El contenedor orchestrator no arrancó | `docker compose logs orchestrator` para ver el error |
| Error de conexión a Ollama | Ollama no está corriendo | Abrir Ollama desde el menú inicio de Windows |
| El modelo no responde | El modelo no está descargado | Ejecutar `ollama pull llama3.1:8b` |
| Puerto 3000 o 8000 ocupado | Otro proceso usa esos puertos | Cambiar los puertos en `docker-compose.yml` |
| Docker no encuentra el `compose` | Docker Desktop no está corriendo | Abrir Docker Desktop primero |

---

## Resumen rápido

```
1. Instalar Docker Desktop  →  abrir y dejar corriendo
2. Instalar Ollama          →  dejar corriendo en segundo plano
3. ollama pull llama3.1:8b  →  descargar el modelo (~4.7 GB, solo una vez)
4. Ajustar start_demo.bat   →  corregir la ruta de Ollama si es necesario
5. Ejecutar start_demo.bat  →  levanta todo y abre el navegador
6. Abrir http://localhost:3000
```
