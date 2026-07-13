# Proyecto Colegios — Asistente Virtual de Laboratorio
## Documentación Técnica del Proyecto

---

## ¿Qué es este proyecto?

Es un **asistente de laboratorio virtual con inteligencia artificial**, pensado para correr 24/7 en un servidor de bajo costo (ej. una Raspberry Pi) dentro de un colegio con recursos limitados. En lugar de dar respuestas directas, el sistema guía al estudiante con preguntas socráticamente diseñadas para que llegue a la solución por sí mismo.

La demo incluida está especializada en tres dominios de ingeniería (VHDL, RF, Redes) porque así nació el proyecto, pero la arquitectura está pensada para que agregar una asignatura real de colegio sea agregar una carpeta y unas keywords, no reescribir código — ver [Cómo extender el proyecto](#cómo-extender-el-proyecto).

---

## Arquitectura del sistema

```
[ Navegador / celular en la red del colegio (puerto 3000) ]
         │
         ▼
[ nginx — sirve el frontend Y reenvía /api al orchestrator ]
   frontend/index.html  +  frontend/nginx.conf
         │  (fetch a rutas relativas "/api/...", mismo origen)
         ▼
[ Docker: Orchestrator FastAPI (puerto 8000) ]
   ├── router.py + domains.py   → Semantic Routing (sentence-transformers + coseno)
   ├── rag.py + embeddings.py   → RAG con FAISS, filtrado por dominio, cacheado en disco
   └── main.py                  → Orquesta todo: umbrales, historial, cola, logging, LLM
         │
         ▼
[ Ollama — corre NATIVO en el host (puerto 11434) ]
```

**¿Por qué Ollama corre fuera de Docker?**
En Windows con GPU dedicada (ej. RTX 3060), porque Docker Desktop no puede acceder directamente a la GPU NVIDIA. En Linux / Raspberry Pi, porque instalarlo como servicio del sistema (`systemctl status ollama`) es más simple de operar y actualizar que meterlo en el mismo compose. El contenedor se comunica con Ollama vía `OLLAMA_HOST` (ver `.env.example`).

### Flujo de una consulta

1. El usuario escribe una pregunta en el chat (el frontend mantiene el historial de la conversación en memoria y lo reenvía en cada request).
2. **Semantic Router** (`router.py` + `domains.py`): convierte la pregunta en un embedding y lo compara por similitud coseno con centroides de cada dominio (definidos por keywords en `domains.py`). Si la confianza del mejor dominio queda por debajo de `MIN_ROUTING_CONFIDENCE`, el sistema responde honestamente que no tiene material sobre ese tema **sin llamar al LLM** (ahorra cómputo, importante en hardware limitado).
3. **RAG** (`rag.py`): busca en la base de conocimiento del dominio enrutado (`knowledge_base/<dominio>/*.md`) los fragmentos más relevantes usando FAISS, filtrando por dominio y por un score mínimo (`MIN_CHUNK_SCORE`). Si ningún fragmento supera el umbral, también se corta ahí con una respuesta honesta.
4. **LLM** (`main.py`): envía la pregunta + contexto recuperado + historial reciente a Ollama con un prompt socrático estricto (en español). El modelo genera 1-2 oraciones y una pregunta guía, sin revelar la respuesta. Las llamadas al LLM pasan por una cola (`MAX_CONCURRENT_GENERATIONS`) para no saturar hardware limitado.
5. La interacción se registra de forma anónima en SQLite (sin datos identificables del alumno) para que, a futuro, un profesor pueda ver qué temas se consultan más.
6. El frontend muestra la respuesta y visualiza el pipeline interno (scores reales de routing, chunks recuperados, pasos ejecutados) — colapsado detrás de un botón en pantallas angostas (celulares).

---

## Archivos del proyecto

```
proyecto_colegios/
├── docker-compose.yml                  # Servicios: orchestrator + frontend, volúmenes, healthcheck
├── .env.example                        # Variables de configuración documentadas
├── start_demo.bat / stop_demo.bat      # Scripts Windows
├── start.sh / stop.sh                  # Scripts Linux / Raspberry Pi
├── frontend/
│   ├── index.html                      # UI completa (HTML + CSS + JS), en español, responsive
│   └── nginx.conf                      # Sirve el frontend + proxy /api → orchestrator:8000
└── orchestrator/
    ├── Dockerfile                      # Imagen Docker; pre-descarga el modelo de embeddings
    ├── requirements.txt                # Dependencias Python (runtime)
    ├── requirements-dev.txt            # + pytest (tests)
    ├── pytest.ini
    ├── main.py                         # FastAPI: endpoints, umbrales, historial, cola, logging
    ├── router.py                       # Enrutador semántico
    ├── rag.py                          # Pipeline RAG con FAISS (persistente en disco, por dominio)
    ├── embeddings.py                   # Carga compartida del modelo de embeddings
    ├── domains.py                      # Keywords y labels por dominio/asignatura
    ├── tests/                          # pytest
    └── knowledge_base/
        ├── vhdl/vhdl_guide.md
        ├── rf/rf_signals.md
        └── network/network_protocols.md
```

### ¿Qué hace cada archivo Python?

- **`main.py`**: Punto de entrada. Define los endpoints REST (`/health`, `/query`, `/ollama-status`, `/stats`, `/reindex`). Orquesta router → RAG → LLM, aplica los umbrales de confianza, gestiona la cola de generación, guarda el historial de conversación y registra interacciones anónimas.
- **`router.py`**: Clasifica consultas por similitud coseno contra centroides de dominio (definidos en `domains.py`).
- **`rag.py`**: Lee los `.md` de `knowledge_base/<dominio>/`, los divide en chunks respetando párrafos y palabras (no corta a la mitad), construye un índice FAISS y lo cachea en disco (se reconstruye solo si el contenido de la KB cambió). `retrieve()` filtra por dominio y por score mínimo.
- **`embeddings.py`**: Carga el modelo `all-MiniLM-L6-v2` una sola vez y lo comparte entre `router.py` y `rag.py` (antes se cargaba dos veces, duplicando RAM — relevante en una Raspberry Pi).
- **`domains.py`**: Única fuente de verdad para las keywords y el nombre visible de cada dominio/asignatura.

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

## Variables de configuración

Ver `.env.example` para la lista completa con comentarios. Las más importantes para el despliegue:

| Variable | Qué controla |
|---|---|
| `OLLAMA_HOST` | Cómo llega el contenedor a Ollama. Distinto en Windows/Mac (`host.docker.internal`) vs. Linux (normalmente la IP del bridge de Docker). |
| `MODEL_NAME` | Modelo LLM. Debe coincidir con lo que se descargó con `ollama pull`. |
| `MAX_CONCURRENT_GENERATIONS` | Cuántas respuestas genera Ollama a la vez. En Raspberry Pi, dejar en `1`. |
| `MIN_ROUTING_CONFIDENCE`, `MIN_CHUNK_SCORE` | Umbrales para no responder fuera de dominio ni alucinar sin contexto real. **Requieren calibración** — ver más abajo. |
| `ALLOWED_ORIGINS` | CORS. Con el proxy de nginx (rutas `/api/...`) casi no hace falta tocarlo; solo importa si se accede al puerto 8000 directamente desde otro origen. |

### Calibrar los umbrales de confianza

Los umbrales por defecto (`MIN_ROUTING_CONFIDENCE=0.28`, `MIN_CHUNK_SCORE=0.20`) se probaron contra las tres asignaturas de la demo (VHDL, RF, Redes): consultas en dominio superaron 0.3–0.6 de confianza, mientras que consultas claramente fuera de dominio ("cuál es la capital de Francia", "receta de galletas") dieron confianza entre -0.03 y 0.06. Con esos valores, el sistema distinguió correctamente ambos casos en las pruebas manuales.

Estos números **van a cambiar** en cuanto se reemplacen los dominios por asignaturas reales de colegio, porque dependen del vocabulario de las keywords en `domains.py` y del contenido real de `knowledge_base/`. Procedimiento recomendado al agregar una asignatura nueva:

1. Escribir 5-10 preguntas típicas de esa asignatura y 5-10 preguntas claramente ajenas.
2. Pegarlas una por una en el chat (o con `curl -X POST /query`) y mirar el campo `routing.confidence` en la respuesta (o el panel "Scores de Enrutamiento Semántico" en la UI).
3. Elegir un umbral entre el mínimo de las preguntas en-dominio y el máximo de las preguntas fuera de dominio.
4. Ajustar `MIN_ROUTING_CONFIDENCE` / `MIN_CHUNK_SCORE` en `.env` y reiniciar.

---

## Requisitos para ejecutar el proyecto

### Software

| Requisito | Descarga |
|---|---|
| **Docker** (Desktop en Windows/Mac, Engine en Linux) | https://www.docker.com/ |
| **Ollama** | https://ollama.com/download |

> No se necesita Python instalado localmente — todo corre en contenedores.

### Hardware

| Escenario | RAM | Modelo recomendado |
|---|---|---|
| PC con GPU dedicada (ej. RTX 3060) | 16 GB+ | `llama3.1:8b` |
| Raspberry Pi 5 (8 GB) | 8 GB | `llama3.2:3b-instruct-q4_K_M` (default) |
| Hardware muy limitado | 4 GB | `qwen2.5:1.5b-instruct` o `gemma2:2b-instruct-q4_K_M` |

Independientemente del modelo elegido, medir tokens/segundo reales en el hardware objetivo antes de dar el despliegue por definitivo — la tabla de arriba es un punto de partida, no una garantía.

---

## Pasos para ejecutar el proyecto

### Windows

1. Instalar [Docker Desktop](https://www.docker.com/products/docker-desktop) y dejarlo corriendo.
2. Instalar [Ollama](https://ollama.com/download) (corre como servicio en segundo plano).
3. `cp .env.example .env` y ajustar `MODEL_NAME` si hace falta.
4. `ollama pull <modelo elegido>`.
5. Ejecutar `start_demo.bat`.
6. Abrir `http://localhost:3000`.
7. Para detener: `stop_demo.bat`.

### Linux / Raspberry Pi

1. Instalar Docker Engine + plugin compose (`sudo apt install docker.io docker-compose-plugin`, o el script oficial de Docker).
2. Instalar Ollama: `curl -fsSL https://ollama.com/install.sh | sh` (se instala como servicio systemd).
3. `cp .env.example .env`. Ajustar `OLLAMA_HOST` — normalmente la IP del bridge de Docker (`ip addr show docker0`, suele ser `172.17.0.1`) en vez de `host.docker.internal`, que es específico de Docker Desktop.
4. `chmod +x start.sh stop.sh && ./start.sh` (el script descarga el modelo, construye las imágenes y espera a que el health check pase).
5. Abrir `http://localhost:3000`, o `http://<ip-de-la-pi>:3000` desde cualquier dispositivo de la red del colegio.
6. Para que el servidor se recupere solo tras un corte de energía: `sudo systemctl enable docker` (Docker Desktop en Windows ya arranca con el sistema; en Linux hay que habilitarlo explícitamente).
7. Para detener: `./stop.sh`.

### Sin scripts (cualquier plataforma)

```bash
docker compose up -d --build
```

---

## Cómo extender el proyecto

### Agregar una asignatura/dominio nuevo

1. Crear `orchestrator/knowledge_base/<dominio>/` con uno o más `.md`.
2. Agregar keywords en `orchestrator/domains.py` → `DOMAIN_KEYWORDS["<dominio>"]`.
3. Agregar el nombre visible en `DOMAIN_LABELS["<dominio>"]`.
4. Agregar el chip visual en `frontend/index.html` (bloque `.agents-bar`, y el mapa `labels`/`chipMap` dentro del `<script>`).
5. Llamar a `POST /reindex` (no hace falta reconstruir la imagen: `knowledge_base/` está montada como volumen).
6. Calibrar los umbrales de confianza (ver sección anterior) con preguntas reales de esa asignatura.

`orchestrator/tests/test_domains_kb_consistency.py` falla automáticamente si una carpeta de `knowledge_base/` no tiene su entrada en `domains.py`, o viceversa — corre esos tests después de agregar un dominio.

### Agregar más conocimiento a una asignatura existente

Editar o agregar archivos `.md` en la carpeta del dominio dentro de `knowledge_base/`. Separar secciones con `\n---\n` para mejor chunking (cada sección se sub-divide respetando párrafos y palabras si es muy larga). Llamar a `POST /reindex` para aplicar los cambios sin reiniciar el contenedor.

### Cambiar el modelo LLM

Editar `MODEL_NAME` en `.env` y hacer `ollama pull <nuevo-modelo>` antes de reiniciar. Revisar también `OLLAMA_NUM_CTX` si el modelo nuevo soporta (o necesita) una ventana de contexto distinta.

---

## Endpoints de la API

| Endpoint | Método | Descripción |
|---|---|---|
| `/health` | GET | Estado del orchestrator. |
| `/ollama-status` | GET | Verifica conectividad con Ollama y lista modelos disponibles. |
| `/query` | POST | `{query, history}` → routing + chunks recuperados + respuesta socrática + pasos del pipeline. |
| `/reindex` | POST | Reconstruye el índice RAG desde `knowledge_base/` sin reiniciar el contenedor. |
| `/stats` | GET | Conteo anónimo de interacciones por dominio (base para un futuro panel docente). |

Documentación interactiva completa en `/docs` (generada automáticamente por FastAPI).

---

## Solución de problemas frecuentes

| Problema | Causa probable | Solución |
|---|---|---|
| El frontend muestra "Sin conexión" | El contenedor orchestrator no arrancó | `docker compose logs orchestrator` |
| Error de conexión a Ollama / respuestas 503 | Ollama no está corriendo, o `OLLAMA_HOST` está mal | Verificar `ollama list`; revisar `OLLAMA_HOST` en `.env` (distinto en Windows vs. Linux) |
| El modelo no responde | El modelo no está descargado, o no coincide con `MODEL_NAME` | `ollama pull <modelo>` — confirmar que coincide exactamente con `.env` |
| Cambié un `.md` y no pasa nada | La KB está montada como volumen pero el índice no se reconstruye solo | `POST /reindex` |
| Puerto 3000 u 8000 ocupado | Otro proceso usa esos puertos | Cambiar los puertos en `docker-compose.yml` |
| Docker no encuentra `compose` | Docker no está corriendo, o falta el plugin compose en Linux | Abrir Docker Desktop, o `sudo apt install docker-compose-plugin` |
| Respuestas muy lentas o se acumulan | Hardware limitado con varias consultas simultáneas | Es esperado con `MAX_CONCURRENT_GENERATIONS=1`; el panel de pipeline muestra cuántas consultas había en cola |

---

## Tests y CI

```bash
cd orchestrator
pip install -r requirements-dev.txt
pytest -v
```

- `tests/test_rag_chunking.py`: chunking por párrafos/palabras y carga de la base de conocimiento — no requiere el modelo de embeddings.
- `tests/test_domains_kb_consistency.py`: detecta desincronización entre `knowledge_base/` y `domains.py` — tampoco requiere el modelo.
- `tests/test_router.py`: enrutamiento semántico real — descarga el modelo de embeddings la primera vez que corre (ya viene pre-descargado dentro de la imagen Docker).

`.github/workflows/ci.yml` corre estos tests en cada push/PR y además construye la imagen del orchestrator para `linux/arm64` (arquitectura de Raspberry Pi) para detectar roturas de plataforma sin necesidad de tener el hardware a mano.

---

## Resumen rápido

```
1. Instalar Docker                    →  Desktop (Win/Mac) o Engine (Linux)
2. Instalar Ollama                    →  dejar corriendo en segundo plano / como servicio
3. cp .env.example .env               →  ajustar MODEL_NAME y OLLAMA_HOST
4. ollama pull <modelo>               →  el mismo que quedó en MODEL_NAME
5. start_demo.bat  o  ./start.sh      →  levanta todo y valida el health check
6. Abrir http://localhost:3000 (o la IP del servidor desde otro dispositivo)
```
