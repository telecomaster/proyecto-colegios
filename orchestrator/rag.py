"""
RAG Pipeline - indexes the knowledge base and retrieves relevant chunks.
Uses FAISS for efficient vector similarity search.

Knowledge base layout: knowledge_base/<domain>/*.md
Each subfolder name is a domain id matching domains.DOMAIN_KEYWORDS/DOMAIN_LABELS.
"""
import hashlib
import json
import os

import faiss
import numpy as np

from embeddings import get_model

KB_PATH = os.getenv("KB_PATH", "/app/knowledge_base")
CACHE_DIR = os.getenv("RAG_CACHE_DIR", "/app/.rag_cache")
CHUNK_SIZE = 300  # characters per chunk (soft limit, paragraph/word aware)
OVERLAP = 50
TOP_K = 3

chunks: list[str] = []
chunk_domains: list[str] = []
index = None


def _split_on_words(text: str, max_size: int, overlap: int) -> list[str]:
    """Fallback splitter for paragraphs longer than max_size. Cuts on word
    boundaries instead of raw character offsets so words are never broken."""
    words = text.split(" ")
    result = []
    current: list[str] = []
    current_len = 0
    for word in words:
        if current_len + len(word) + 1 > max_size and current:
            result.append(" ".join(current))
            overlap_words: list[str] = []
            overlap_len = 0
            for w in reversed(current):
                if overlap_len + len(w) + 1 > overlap:
                    break
                overlap_words.insert(0, w)
                overlap_len += len(w) + 1
            current, current_len = overlap_words, overlap_len
        current.append(word)
        current_len += len(word) + 1
    if current:
        result.append(" ".join(current))
    return result


def _pack_paragraphs(paragraphs: list[str], max_size: int, overlap: int) -> list[str]:
    """Greedily packs paragraphs into chunks up to max_size, preferring to
    break between paragraphs rather than mid-sentence or mid-word."""
    result = []
    current: list[str] = []
    current_len = 0
    for para in (p.strip() for p in paragraphs):
        if not para:
            continue
        if len(para) > max_size:
            if current:
                result.append("\n\n".join(current))
                current, current_len = [], 0
            result.extend(_split_on_words(para, max_size, overlap))
            continue
        if current_len + len(para) + 2 > max_size and current:
            result.append("\n\n".join(current))
            if overlap > 0 and len(current[-1]) <= overlap:
                current, current_len = [current[-1]], len(current[-1])
            else:
                current, current_len = [], 0
        current.append(para)
        current_len += len(para) + 2
    if current:
        result.append("\n\n".join(current))
    return result


def load_and_chunk_documents() -> tuple[list[str], list[str]]:
    all_chunks: list[str] = []
    all_domains: list[str] = []
    if not os.path.isdir(KB_PATH):
        return all_chunks, all_domains

    for domain in sorted(os.listdir(KB_PATH)):
        domain_path = os.path.join(KB_PATH, domain)
        if not os.path.isdir(domain_path):
            continue
        for fname in sorted(os.listdir(domain_path)):
            if not fname.endswith(".md"):
                continue
            with open(os.path.join(domain_path, fname), "r", encoding="utf-8") as f:
                text = f.read()
            for section in text.split("\n---\n"):
                paragraphs = section.split("\n\n")
                for chunk in _pack_paragraphs(paragraphs, CHUNK_SIZE, OVERLAP):
                    if chunk.strip():
                        all_chunks.append(chunk)
                        all_domains.append(domain)
    return all_chunks, all_domains


def _kb_fingerprint() -> str:
    """Content hash of the whole knowledge base, used to decide whether a
    cached FAISS index can be reused instead of re-embedding everything."""
    h = hashlib.sha256()
    if not os.path.isdir(KB_PATH):
        return h.hexdigest()
    for domain in sorted(os.listdir(KB_PATH)):
        domain_path = os.path.join(KB_PATH, domain)
        if not os.path.isdir(domain_path):
            continue
        for fname in sorted(os.listdir(domain_path)):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(domain_path, fname)
            h.update(fpath.encode("utf-8"))
            with open(fpath, "rb") as f:
                h.update(f.read())
    return h.hexdigest()


def _cache_paths() -> tuple[str, str]:
    return (
        os.path.join(CACHE_DIR, "index.faiss"),
        os.path.join(CACHE_DIR, "meta.json"),
    )


def _load_cache(fingerprint: str) -> bool:
    global chunks, chunk_domains, index
    index_path, meta_path = _cache_paths()
    if not (os.path.exists(index_path) and os.path.exists(meta_path)):
        return False
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        if meta.get("fingerprint") != fingerprint:
            return False
        loaded_index = faiss.read_index(index_path)
    except Exception:
        return False
    chunks = meta["chunks"]
    chunk_domains = meta["chunk_domains"]
    index = loaded_index
    return True


def _save_cache(fingerprint: str) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    index_path, meta_path = _cache_paths()
    faiss.write_index(index, index_path)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({"fingerprint": fingerprint, "chunks": chunks, "chunk_domains": chunk_domains}, f)


def build_index(force: bool = False) -> None:
    global chunks, chunk_domains, index
    fingerprint = _kb_fingerprint()

    if not force and _load_cache(fingerprint):
        print(f"[RAG] Loaded cached index: {len(chunks)} chunks.")
        return

    chunks, chunk_domains = load_and_chunk_documents()
    if not chunks:
        index = None
        print("[RAG] WARNING: no documents found in knowledge base — retrieval disabled.")
        return

    model = get_model()
    embeddings = model.encode(chunks, show_progress_bar=False)
    embeddings = np.array(embeddings, dtype="float32")
    faiss.normalize_L2(embeddings)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # Inner product = cosine after normalization
    index.add(embeddings)
    _save_cache(fingerprint)
    print(f"[RAG] Index built: {len(chunks)} chunks from knowledge base.")


def chunk_count() -> int:
    return len(chunks)


def retrieve(query: str, k: int = TOP_K, domain: str | None = None, min_score: float = 0.0) -> list[dict]:
    if index is None or index.ntotal == 0:
        return []
    model = get_model()
    query_vec = model.encode([query], show_progress_bar=False)
    query_vec = np.array(query_vec, dtype="float32")
    faiss.normalize_L2(query_vec)

    # Sobre-buscamos para poder filtrar por dominio sin perder cobertura,
    # ya que FAISS no filtra por metadata de forma nativa.
    search_k = min(index.ntotal, max(k * 5, k))
    scores, indices = index.search(query_vec, search_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        if domain is not None and chunk_domains[idx] != domain:
            continue
        if score < min_score:
            continue
        results.append({
            "chunk": chunks[idx],
            "domain": chunk_domains[idx],
            "score": round(float(score), 4),
        })
        if len(results) >= k:
            break
    return results
