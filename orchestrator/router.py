"""
Semantic Router - classifies student queries to the correct domain agent.
Uses cosine similarity between query embeddings and domain centroids.
"""
import numpy as np

from domains import DOMAIN_KEYWORDS, DOMAIN_LABELS
from embeddings import get_model

DOMAIN_CENTROIDS = {}


def build_centroids() -> None:
    model = get_model()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        embeddings = model.encode(keywords)
        DOMAIN_CENTROIDS[domain] = np.mean(embeddings, axis=0)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))


def route_query(query: str) -> dict:
    if not DOMAIN_CENTROIDS:
        build_centroids()

    model = get_model()
    query_embedding = model.encode([query])[0]
    scores = {}
    for domain, centroid in DOMAIN_CENTROIDS.items():
        scores[domain] = cosine_similarity(query_embedding, centroid)

    best_domain = max(scores, key=scores.get)
    return {
        "domain": best_domain,
        "agent": DOMAIN_LABELS[best_domain],
        "scores": {k: round(v, 4) for k, v in scores.items()},
        "confidence": round(scores[best_domain], 4),
    }
