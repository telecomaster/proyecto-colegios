"""
RAG Pipeline - indexes the knowledge base and retrieves relevant chunks.
Uses FAISS for efficient vector similarity search.
"""
import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

KB_PATH = "/app/knowledge_base"
CHUNK_SIZE = 300  # characters per chunk
OVERLAP = 50
TOP_K = 3

chunks = []
index = None

def load_and_chunk_documents():
    all_chunks = []
    for fname in os.listdir(KB_PATH):
        if fname.endswith(".md"):
            with open(os.path.join(KB_PATH, fname), "r", encoding="utf-8") as f:
                text = f.read()
            # Split by sections first, then by size
            sections = text.split("\n---\n")
            for section in sections:
                section = section.strip()
                if not section:
                    continue
                # Further chunk large sections
                if len(section) <= CHUNK_SIZE + OVERLAP:
                    all_chunks.append(section)
                else:
                    start = 0
                    while start < len(section):
                        end = min(start + CHUNK_SIZE, len(section))
                        all_chunks.append(section[start:end])
                        start += CHUNK_SIZE - OVERLAP
    return all_chunks

def build_index():
    global chunks, index
    chunks = load_and_chunk_documents()
    embeddings = model.encode(chunks, show_progress_bar=False)
    embeddings = np.array(embeddings, dtype="float32")
    faiss.normalize_L2(embeddings)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # Inner product = cosine after normalization
    index.add(embeddings)
    print(f"[RAG] Index built: {len(chunks)} chunks from knowledge base.")

def retrieve(query: str, k: int = TOP_K) -> list[dict]:
    if index is None:
        return []
    query_vec = model.encode([query], show_progress_bar=False)
    query_vec = np.array(query_vec, dtype="float32")
    faiss.normalize_L2(query_vec)
    scores, indices = index.search(query_vec, k)
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx >= 0:
            results.append({
                "chunk": chunks[idx],
                "score": round(float(score), 4)
            })
    return results

# Build index on module load
build_index()
