"""
FastAPI Orchestrator - main entry point for the demo system.
Handles semantic routing, RAG retrieval, and LLM invocation.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import json

import os
from router import route_query
from rag import retrieve

app = FastAPI(title="Proyecto Colegios - LLM Virtual Lab Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
MODEL_NAME = "llama3.1:8b"

SOCRATIC_SYSTEM_PROMPT = """You are a Socratic tutor. You have access to a CONTEXT extracted from the faculty knowledge base. You MUST base your response exclusively on this CONTEXT.

STRICT RULES:
1. DO NOT write any code. DO NOT give the answer. DO NOT solve the problem.
2. Read the CONTEXT carefully. Find the key concept the student is missing.
3. Write 1-2 sentences pointing the student toward that concept without revealing it.
4. End with ONE question that makes the student think about the specific concept in the CONTEXT.
5. Maximum 3 sentences total. Be concise.

CONTEXT FROM KNOWLEDGE BASE:
{context}

Remember: Your only job is to ask one guiding question based on the CONTEXT above."""


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    query: str
    routing: dict
    retrieved_chunks: list
    llm_response: str
    steps: list[str]


@app.get("/health")
async def health():
    return {"status": "ok", "service": "Proyecto Colegios Orchestrator"}


@app.get("/ollama-status")
async def ollama_status():
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            models = r.json().get("models", [])
            names = [m["name"] for m in models]
            return {"status": "connected", "models": names}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.post("/query", response_model=QueryResponse)
async def process_query(req: QueryRequest):
    steps = []

    # Step 1: Semantic Routing
    steps.append("Step 1: Semantic routing — analyzing query intent...")
    routing = route_query(req.query)
    steps.append(
        f"Routed to: {routing['agent']} "
        f"(confidence: {routing['confidence']}, scores: {routing['scores']})"
    )

    # Step 2: RAG Retrieval
    steps.append("Step 2: RAG retrieval — searching knowledge base...")
    retrieved = retrieve(req.query, k=3)
    steps.append(f"Retrieved {len(retrieved)} relevant chunks from faculty knowledge base.")

    context = "\n\n---\n\n".join(
        [f"[Chunk {i+1} | score={r['score']}]\n{r['chunk']}"
         for i, r in enumerate(retrieved)]
    )

    # Step 3: LLM Generation (Socratic)
    steps.append(f"Step 3: Invoking {routing['agent']} with Socratic prompting...")
    system_prompt = SOCRATIC_SYSTEM_PROMPT.format(context=context)
    llm_response = await call_ollama(req.query, system_prompt)
    steps.append("Response generated.")

    return QueryResponse(
        query=req.query,
        routing=routing,
        retrieved_chunks=[{"text": r["chunk"][:200] + "...", "score": r["score"]} for r in retrieved],
        llm_response=llm_response,
        steps=steps,
    )


async def call_ollama(user_message: str, system_prompt: str) -> str:
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 200,
        }
    }
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
            r.raise_for_status()
            data = r.json()
            return data["message"]["content"]
    except Exception as e:
        return f"[LLM Error] Could not reach Ollama: {str(e)}"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
