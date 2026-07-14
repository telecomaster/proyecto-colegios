"""
FastAPI Orchestrator - main entry point for the demo system.
Handles semantic routing, RAG retrieval, and LLM invocation.
"""
import asyncio
import json
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import rag
import router as router_module
from domains import DOMAIN_LABELS
from rag import retrieve
from router import route_query

OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.2:3b-instruct-q4_K_M")
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "2048"))
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "120"))

# Cuantos generaciones concurrentes tolera el modelo. En una Raspberry Pi
# esto casi siempre debe quedar en 1: Ollama solo puede generar una
# respuesta a la vez de forma eficiente en ese hardware.
MAX_CONCURRENT_GENERATIONS = int(os.getenv("MAX_CONCURRENT_GENERATIONS", "1"))

# Umbrales de confianza para no inventar respuestas fuera de dominio o sin
# contexto real en la base de conocimiento. Se calibran con consultas reales;
# ver DOCUMENTACION.md para el procedimiento.
MIN_ROUTING_CONFIDENCE = float(os.getenv("MIN_ROUTING_CONFIDENCE", "0.28"))
MIN_CHUNK_SCORE = float(os.getenv("MIN_CHUNK_SCORE", "0.20"))

# Cuantos mensajes previos (usuario + asistente) se reenvian al LLM como
# contexto conversacional. Limitado para no agotar num_ctx en la Pi.
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "8"))

ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

LOG_DB_PATH = os.getenv("LOG_DB_PATH", "/app/data/interactions.db")

SOCRATIC_SYSTEM_PROMPT = """Eres un tutor socrático. Tienes acceso a un CONTEXTO extraído de la base de conocimiento de la asignatura. DEBES basar tu respuesta exclusivamente en este CONTEXTO.

REGLAS ESTRICTAS:
1. NO escribas código. NO des la respuesta. NO resuelvas el problema.
2. Lee el CONTEXTO con atención. Identifica el concepto clave que le falta al estudiante.
3. Escribe 1-2 oraciones que orienten al estudiante hacia ese concepto sin revelarlo.
4. Termina con UNA pregunta que lo haga pensar en el concepto específico del CONTEXTO.
5. Máximo 3 oraciones en total. Sé breve.
6. Responde siempre en español.

CONTEXTO DE LA BASE DE CONOCIMIENTO:
{context}

Recuerda: tu único trabajo es hacer una pregunta guía basada en el CONTEXTO anterior."""


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class QueryRequest(BaseModel):
    query: str
    history: list[ChatMessage] = []


# --- Cola de generación --------------------------------------------------
# Reporta cuantas solicitudes estaban en curso o esperando cuando esta
# solicitud entró, para que el panel de pipeline sea honesto sobre la carga
# del sistema (relevante con hardware limitado como una Raspberry Pi).
_generation_semaphore = asyncio.Semaphore(MAX_CONCURRENT_GENERATIONS)
_queue_lock = asyncio.Lock()
_queue_count = 0


async def _enter_queue() -> int:
    global _queue_count
    async with _queue_lock:
        _queue_count += 1
        return _queue_count


async def _leave_queue() -> None:
    global _queue_count
    async with _queue_lock:
        _queue_count = max(0, _queue_count - 1)


# --- Registro anónimo de interacciones ------------------------------------
def _init_log_db() -> None:
    os.makedirs(os.path.dirname(LOG_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(LOG_DB_PATH)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                domain TEXT,
                confidence REAL,
                query TEXT NOT NULL,
                response TEXT NOT NULL,
                chunks_retrieved INTEGER NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def _log_interaction_sync(query: str, routing: dict, chunks_retrieved: int, response: str) -> None:
    conn = sqlite3.connect(LOG_DB_PATH)
    try:
        conn.execute(
            "INSERT INTO interactions (ts, domain, confidence, query, response, chunks_retrieved) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(),
                routing.get("domain"),
                routing.get("confidence"),
                query,
                response,
                chunks_retrieved,
            ),
        )
        conn.commit()
    finally:
        conn.close()


async def _log_interaction(query: str, routing: dict, chunks_retrieved: int, response: str) -> None:
    # No debe poder tumbar una respuesta al estudiante si el logging falla.
    try:
        await asyncio.to_thread(_log_interaction_sync, query, routing, chunks_retrieved, response)
    except Exception as e:
        print(f"[LOG] No se pudo registrar la interacción: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _init_log_db()
    router_module.build_centroids()
    await asyncio.to_thread(rag.build_index)
    app.state.http_client = httpx.AsyncClient(timeout=OLLAMA_TIMEOUT)
    yield
    await app.state.http_client.aclose()


app = FastAPI(title="Proyecto Colegios - LLM Virtual Lab Assistant", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "Proyecto Colegios Orchestrator"}


@app.get("/ollama-status")
async def ollama_status():
    try:
        r = await app.state.http_client.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        models = r.json().get("models", [])
        names = [m["name"] for m in models]
        return {"status": "connected", "models": names}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.get("/stats")
async def stats():
    def _query():
        conn = sqlite3.connect(LOG_DB_PATH)
        try:
            rows = conn.execute("SELECT domain, COUNT(*) FROM interactions GROUP BY domain").fetchall()
            by_domain = dict(rows)
            return {"total_interactions": sum(by_domain.values()), "by_domain": by_domain}
        finally:
            conn.close()

    return await asyncio.to_thread(_query)


@app.post("/reindex")
async def reindex():
    """Reconstruye el índice RAG desde disco sin reiniciar el contenedor.
    Pensado para que un profesor agregue material a knowledge_base/ (montado
    como volumen) y lo active sin tocar Docker."""
    await asyncio.to_thread(rag.build_index, True)
    return {"status": "ok", "chunks_indexed": rag.chunk_count()}


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _shorten(chunk: dict) -> dict:
    text = chunk["chunk"]
    return {"text": text[:200] + ("..." if len(text) > 200 else ""), "score": chunk["score"]}


async def _stream_query(req: QueryRequest):
    steps = []

    # Paso 1: enrutamiento semántico
    steps.append("Paso 1: enrutamiento semántico — analizando la intención de la consulta...")
    routing = route_query(req.query)
    steps.append(
        f"Enrutado a: {routing['agent']} "
        f"(confianza: {routing['confidence']}, scores: {routing['scores']})"
    )
    yield _sse({"type": "meta", "routing": routing, "steps": steps, "retrieved_chunks": []})

    if routing["confidence"] < MIN_ROUTING_CONFIDENCE:
        steps.append("Confianza de enrutamiento por debajo del umbral — no hay un agente claro para esta consulta.")
        fallback = (
            "Todavía no tengo material sobre ese tema. Puedo ayudarte con: "
            + ", ".join(DOMAIN_LABELS.values())
            + ". ¿Tu pregunta se relaciona con alguno de estos temas?"
        )
        yield _sse({"type": "token", "delta": fallback})
        yield _sse({"type": "done", "steps": steps, "retrieved_chunks": [], "full_response": fallback})
        await _log_interaction(req.query, routing, 0, fallback)
        return

    # Paso 2: recuperación RAG, filtrada al dominio enrutado
    steps.append("Paso 2: recuperación RAG — buscando en la base de conocimiento...")
    retrieved = retrieve(req.query, k=3, domain=routing["domain"], min_score=MIN_CHUNK_SCORE)
    steps.append(f"Se recuperaron {len(retrieved)} fragmentos relevantes de la base de conocimiento.")
    retrieved_chunks = [_shorten(r) for r in retrieved]
    yield _sse({"type": "meta", "routing": routing, "steps": steps, "retrieved_chunks": retrieved_chunks})

    if not retrieved:
        steps.append("Ningún fragmento superó el umbral de relevancia — no hay contexto suficiente.")
        fallback = (
            f"Detecté que tu pregunta es sobre {routing['agent']}, pero aún no tengo material "
            "específico sobre ese punto en la base de conocimiento. ¿Puedes reformular la pregunta, "
            "o pedirle a tu profesor que agregue ese tema?"
        )
        yield _sse({"type": "token", "delta": fallback})
        yield _sse({"type": "done", "steps": steps, "retrieved_chunks": [], "full_response": fallback})
        await _log_interaction(req.query, routing, 0, fallback)
        return

    context = "\n\n---\n\n".join(
        [f"[Fragmento {i + 1} | score={r['score']}]\n{r['chunk']}" for i, r in enumerate(retrieved)]
    )

    # Paso 3: generación con el LLM (socrática), token a token
    steps.append(f"Paso 3: invocando al {routing['agent']} con instrucciones socráticas...")
    system_prompt = SOCRATIC_SYSTEM_PROMPT.format(context=context)
    history = [m.model_dump() for m in req.history[-MAX_HISTORY_MESSAGES:]]

    queue_position = await _enter_queue()
    if queue_position > 1:
        steps.append(f"En cola de generación: {queue_position - 1} solicitud(es) por delante.")
    yield _sse({"type": "meta", "routing": routing, "steps": steps, "retrieved_chunks": retrieved_chunks})

    full_response = ""
    try:
        async for delta in call_ollama_stream(req.query, system_prompt, history):
            full_response += delta
            yield _sse({"type": "token", "delta": delta})
    except httpx.HTTPError as e:
        await _leave_queue()
        yield _sse({"type": "error", "detail": f"No se pudo contactar al modelo (Ollama): {e}"})
        return
    await _leave_queue()

    steps.append("Respuesta generada.")
    yield _sse({"type": "done", "steps": steps, "retrieved_chunks": retrieved_chunks, "full_response": full_response})
    await _log_interaction(req.query, routing, len(retrieved), full_response)


@app.post("/query")
async def process_query(req: QueryRequest):
    return StreamingResponse(
        _stream_query(req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def call_ollama_stream(user_message: str, system_prompt: str, history: list[dict]):
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": True,
        "keep_alive": OLLAMA_KEEP_ALIVE,
        "options": {
            "temperature": 0.1,
            "num_predict": 200,
            "num_ctx": OLLAMA_NUM_CTX,
        },
    }
    async with _generation_semaphore:
        async with app.state.http_client.stream(
            "POST", f"{OLLAMA_URL}/api/chat", json=payload, timeout=OLLAMA_TIMEOUT
        ) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line.strip():
                    continue
                data = json.loads(line)
                content = data.get("message", {}).get("content", "")
                if content:
                    yield content
                if data.get("done"):
                    break


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
