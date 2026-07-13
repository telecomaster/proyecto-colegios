"""
Modulo de embeddings compartido.
router.py y rag.py necesitan el mismo modelo de sentence-transformers;
cargarlo una sola vez evita duplicar ~90 MB de RAM (critico en Raspberry Pi).
"""
import os
from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")

_model = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model
