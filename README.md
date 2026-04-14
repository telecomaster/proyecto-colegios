# Virtual Lab Assistant — Proyecto Colegios

Asistente de laboratorio virtual con IA que guía a estudiantes de ingeniería mediante el **método socrático** — sin dar respuestas directas, sino haciendo preguntas que los llevan a comprender el concepto por sí mismos.

## Dominios soportados

| Agente | Temas |
|---|---|
| **VHDL/Verilog** | Diseño digital, circuitos sincrónicos, simulación |
| **RF Signal Analysis** | Modulación, espectro, antenas |
| **Network Protocols** | TCP/IP, enrutamiento OSPF/RIP, VLANs |

## Arquitectura

```
Navegador (puerto 3000)
       │
       ▼
nginx — frontend/index.html
       │  REST API
       ▼
FastAPI Orchestrator (puerto 8000)
   ├── Semantic Router   (sentence-transformers + coseno)
   ├── RAG Pipeline      (FAISS + knowledge_base/)
   └── LLM Socratic      (prompt socrático estricto)
       │
       ▼
Ollama — nativo en Windows (puerto 11434)
modelo: llama3.1:8b
```

> Ollama corre fuera de Docker para aprovechar la GPU directamente.

## Requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop)
- [Ollama](https://ollama.com/download)

No se necesita Python instalado localmente.

## Instalación y uso

**1. Descargar el modelo LLM** (solo la primera vez, ~4.7 GB):
```bash
ollama pull llama3.1:8b
```

**2. Ajustar la ruta de Ollama en `start_demo.bat`:**

Buscar esta línea y reemplazarla con la ruta donde quedó instalado Ollama en tu máquina:
```bat
set OLLAMA="C:\Users\TU_USUARIO\AppData\Local\Programs\Ollama\ollama.exe"
```
O simplemente usar:
```bat
set OLLAMA=ollama
```

**3. Iniciar el sistema:**
```bat
start_demo.bat
```

**4. Abrir en el navegador:**

| Servicio | URL |
|---|---|
| Interfaz de chat | http://localhost:3000 |
| API docs | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |

**5. Detener el sistema:**
```bat
stop_demo.bat
```

## Estructura del proyecto

```
proyecto-colegios/
├── docker-compose.yml
├── start_demo.bat
├── stop_demo.bat
├── frontend/
│   └── index.html                  # UI completa (HTML + CSS + JS)
└── orchestrator/
    ├── Dockerfile
    ├── requirements.txt
    ├── main.py                     # FastAPI + prompt socrático
    ├── router.py                   # Enrutador semántico
    ├── rag.py                      # Pipeline RAG con FAISS
    └── knowledge_base/
        └── vhdl_guide.md           # Base de conocimiento
```

## Cómo extender el proyecto

**Agregar un nuevo dominio:**

1. Añadir keywords en `orchestrator/router.py` → `DOMAIN_KEYWORDS`
2. Añadir el label en `DOMAIN_LABELS`
3. Crear un archivo `.md` en `orchestrator/knowledge_base/`
4. Agregar el chip visual en `frontend/index.html`

**Agregar más conocimiento:**

Editar o crear archivos `.md` en `knowledge_base/`. Separar secciones con `\n---\n` para mejor chunking. Los cambios se aplican al reiniciar el contenedor.

**Cambiar el modelo LLM:**

Editar `MODEL_NAME` en `orchestrator/main.py` y ejecutar `ollama pull <modelo>`.

## Solución de problemas

| Problema | Solución |
|---|---|
| Frontend muestra "Offline" | `docker compose logs orchestrator` |
| Error de conexión a Ollama | Abrir Ollama desde el menú inicio |
| Modelo no responde | `ollama pull llama3.1:8b` |
| Puerto ocupado | Cambiar puertos en `docker-compose.yml` |

## Documentación completa

Ver [DOCUMENTACION.md](./DOCUMENTACION.md) para una explicación detallada de la arquitectura, el flujo de datos y todos los pasos de instalación.
