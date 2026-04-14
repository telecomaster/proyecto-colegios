"""
Semantic Router - classifies student queries to the correct domain agent.
Uses cosine similarity between query embeddings and domain centroids.
"""
import numpy as np
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

DOMAIN_KEYWORDS = {
    "vhdl": [
        "vhdl", "verilog", "process sensitivity list", "rising_edge", "falling_edge",
        "std_logic", "std_logic_vector", "vhdl signal", "vhdl entity", "vhdl architecture",
        "behavioral architecture", "synchronous circuit", "flip flop register",
        "vhdl synthesis", "vhdl simulation", "delta cycle simulation",
        "unsigned downto", "port map component", "sequential logic", "combinational logic",
        "setup time hold time", "clock reset counter", "finite state machine vhdl",
        "hardware description language", "digital logic design", "synchronous counter",
        "sensitivity list error", "undefined state simulation", "U state vhdl"
    ],
    "rf": [
        "rf radio frequency", "amplitude modulation", "frequency modulation",
        "spectrum analysis", "antenna design", "signal bandwidth", "carrier wave",
        "noise ratio snr", "fft fourier transform", "decibel power gain",
        "signal attenuation propagation", "wavelength frequency",
        "fm am qam modulation", "ofdm mimo wireless", "beamforming interference",
        "electromagnetic spectrum", "radio wave transmission", "signal processing"
    ],
    "network": [
        "ospf routing protocol", "rip routing protocol", "ospf vs rip",
        "routing protocol comparison", "link state routing", "distance vector routing",
        "tcp ip stack", "network topology", "subnet mask", "bgp autonomous system",
        "ethernet switch router", "firewall vlan", "dhcp dns server",
        "network packet latency", "throughput bandwidth network",
        "osi model layer", "mac address arp", "network protocol",
        "802.1q vlan tagging", "enterprise network", "star topology hub spoke",
        "administrative distance", "convergence routing", "network scalability"
    ]
}

DOMAIN_CENTROIDS = {}

def build_centroids():
    for domain, keywords in DOMAIN_KEYWORDS.items():
        embeddings = model.encode(keywords)
        DOMAIN_CENTROIDS[domain] = np.mean(embeddings, axis=0)

build_centroids()

DOMAIN_LABELS = {
    "vhdl": "VHDL/Verilog Agent",
    "rf": "RF Signal Analysis Agent",
    "network": "Network Protocol Agent"
}

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))

def route_query(query: str) -> dict:
    query_embedding = model.encode([query])[0]
    scores = {}
    for domain, centroid in DOMAIN_CENTROIDS.items():
        scores[domain] = cosine_similarity(query_embedding, centroid)

    best_domain = max(scores, key=scores.get)
    return {
        "domain": best_domain,
        "agent": DOMAIN_LABELS[best_domain],
        "scores": {k: round(v, 4) for k, v in scores.items()},
        "confidence": round(scores[best_domain], 4)
    }
