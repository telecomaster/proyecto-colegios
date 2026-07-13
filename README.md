# Asistente Virtual de Laboratorio — Proyecto Colegios

Asistente de laboratorio virtual con IA que guía a estudiantes mediante el **método socrático** — sin dar respuestas directas, sino haciendo preguntas que los llevan a comprender el concepto por sí mismos. Pensado para correr 24/7 en un servidor de bajo costo (ej. Raspberry Pi) dentro de un colegio.

## Dominios soportados

| Agente | Temas |
|---|---|
| **VHDL/Verilog** | Diseño digital, circuitos sincrónicos, simulación |
| **RF Signal Analysis** | Modulación, espectro, antenas |
| **Network Protocols** | TCP/IP, enrutamiento OSPF/RIP, VLANs |

> Estos son los dominios de la demo original (ingeniería). Para desplegar en un colegio, reemplazar por las asignaturas reales — ver "Cómo extender el proyecto" abajo.

## Arquitectura

```
Navegador / celular (puerto 3000)
       │
       ▼
nginx — frontend/index.html + proxy /api → orchestrator
       │  REST API
       ▼
FastAPI Orchestrator (puerto 8000)
   ├── Semantic Router   (sentence-transformers + coseno, umbral de confianza)
   ├── RAG Pipeline      (FAISS + knowledge_base/<dominio>/*.md, filtrado por dominio)
   ├── Historial         (conversación multi-turno)
   ├── Registro anónimo  (SQLite, sin datos de alumnos)
   └── LLM Socrático     (prompt en español, cola de generación)
       │
       ▼
Ollama — nativo en el host (puerto 11434)
```

> Ollama corre fuera de Docker: en Windows con GPU para aprovecharla directamente; en Linux/Raspberry Pi porque simplifica la instalación (se instala como servicio del sistema).

## Requisitos

- [Docker](https://www.docker.com/) (Docker Desktop en Windows/Mac, Docker Engine en Linux)
- [Ollama](https://ollama.com/download)

No se necesita Python instalado localmente — todo corre en contenedores.

## Instalación y uso

**1. Copiar la configuración de ejemplo:**
```bash
cp .env.example .env
```
Ajustar `MODEL_NAME` según el hardware (ver comentarios en `.env.example`).

**2. Descargar el modelo LLM** (solo la primera vez):
```bash
ollama pull llama3.2:3b-instruct-q4_K_M
```

**3. Iniciar el sistema:**

- **Windows:** doble clic en `start_demo.bat`, o ejecutarlo desde CMD.
- **Linux / Raspberry Pi:**
  ```bash
  chmod +x start.sh stop.sh
  ./start.sh
  ```

**4. Abrir en el navegador:**

| Servicio | URL |
|---|---|
| Interfaz de chat | http://localhost:3000 (o `http://<ip-del-servidor>:3000` desde otro dispositivo en la red) |
| API docs | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |
| Estadísticas de uso (anónimas) | http://localhost:8000/stats |

**5. Detener el sistema:**
```bash
stop_demo.bat      # Windows
./stop.sh          # Linux / Raspberry Pi
```

## Estructura del proyecto

```
proyecto-colegios/
├── docker-compose.yml
├── .env.example
├── start_demo.bat / stop_demo.bat      # Windows
├── start.sh / stop.sh                  # Linux / Raspberry Pi
├── frontend/
│   ├── index.html                      # UI completa (HTML + CSS + JS), en español
│   └── nginx.conf                      # Sirve el frontend y reenvía /api al orchestrator
├── orchestrator/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── requirements-dev.txt            # + pytest, para tests
│   ├── main.py                         # FastAPI: endpoints, historial, umbrales, cola, logging
│   ├── router.py                       # Enrutador semántico
│   ├── rag.py                          # Pipeline RAG con FAISS (persistente, por dominio)
│   ├── embeddings.py                   # Modelo de embeddings compartido
│   ├── domains.py                      # Configuración de dominios/asignaturas
│   ├── tests/                          # pytest — lógica pura, sin necesitar el LLM
│   └── knowledge_base/
│       ├── vhdl/vhdl_guide.md
│       ├── rf/rf_signals.md
│       └── network/network_protocols.md
└── .github/workflows/ci.yml            # Tests + build de imagen arm64
```

## Cómo extender el proyecto

**Agregar una asignatura nueva:**

1. Crear una carpeta `orchestrator/knowledge_base/<dominio>/` con uno o más archivos `.md`.
2. Agregar las keywords del dominio en `orchestrator/domains.py` → `DOMAIN_KEYWORDS`.
3. Agregar el nombre visible en `DOMAIN_LABELS`.
4. Agregar el chip visual correspondiente en `frontend/index.html` (bloque `.agents-bar`).
5. Llamar a `POST /reindex` (o reiniciar el contenedor) para que el RAG indexe el material nuevo.

Un test (`orchestrator/tests/test_domains_kb_consistency.py`) falla si una carpeta de `knowledge_base/` no tiene su entrada correspondiente en `domains.py`, o viceversa.

**Agregar más material a una asignatura existente:**

Editar o crear archivos `.md` dentro de la carpeta del dominio en `knowledge_base/`. Separar secciones con `\n---\n` para mejor chunking. Como esa carpeta está montada como volumen, los cambios se aplican llamando a `POST /reindex` — **no** hace falta reconstruir la imagen ni reiniciar el contenedor.

**Cambiar el modelo LLM:**

Editar `MODEL_NAME` en `.env` y ejecutar `ollama pull <modelo>` antes de reiniciar.

## Notas para Raspberry Pi / hardware limitado

- El modelo por defecto (`llama3.2:3b-instruct-q4_K_M`) está pensado para correr en una Raspberry Pi 5 de 8 GB. Con menos RAM, considerar un modelo más chico (ver `.env.example`).
- `MAX_CONCURRENT_GENERATIONS=1` evita que varias consultas simultáneas degraden todas las respuestas a la vez; las que llegan de más esperan en una cola simple.
- El modelo de embeddings se pre-descarga dentro de la imagen Docker (`Dockerfile`), así que el arranque **no requiere internet**.
- Los umbrales `MIN_ROUTING_CONFIDENCE` / `MIN_CHUNK_SCORE` (en `.env.example`) evitan que el sistema invente respuestas para preguntas fuera de los dominios soportados. Calibrarlos con consultas reales del colegio — ver `DOCUMENTACION.md`.
- Verificar que Docker arranque junto con el sistema operativo (`sudo systemctl enable docker`) para que el servidor se recupere solo después de un corte de energía.

## Solución de problemas

| Problema | Solución |
|---|---|
| Frontend muestra "Sin conexión" | `docker compose logs orchestrator` |
| Error de conexión a Ollama | Verificar que Ollama esté corriendo (`ollama list`) y que `OLLAMA_HOST` en `.env` sea correcto |
| Modelo no responde / 503 | `ollama pull <modelo>` — confirmar que coincide con `MODEL_NAME` |
| Puerto ocupado | Cambiar puertos en `docker-compose.yml` |
| Cambié un `.md` de `knowledge_base/` y no se nota | Llamar a `POST /reindex` (los cambios no se aplican solos) |

## Tests

```bash
cd orchestrator
pip install -r requirements-dev.txt
pytest -v
```

Los tests cubren el chunking del RAG y la consistencia `knowledge_base/` ↔ `domains.py` sin depender del modelo de embeddings; y el enrutador semántico (requiere descargar el modelo la primera vez). CI (`.github/workflows/ci.yml`) corre estos tests y además construye la imagen del orchestrator para `linux/arm64` en cada push, para detectar roturas de plataforma antes de tocar la Raspberry Pi.

## Documentación completa

Ver [DOCUMENTACION.md](./DOCUMENTACION.md) para una explicación detallada de la arquitectura, el flujo de datos y todos los pasos de instalación.
