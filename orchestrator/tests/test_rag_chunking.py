"""
Tests de las funciones puras de chunking en rag.py.
No requieren descargar el modelo de embeddings (get_model() es perezoso),
por eso corren rapido incluso sin GPU/conexion.
"""
import rag


def test_pack_paragraphs_merges_short_paragraphs():
    paragraphs = ["Hola.", "Mundo.", "Adios."]
    chunks = rag._pack_paragraphs(paragraphs, max_size=300, overlap=50)
    assert len(chunks) == 1
    assert "Hola." in chunks[0]
    assert "Mundo." in chunks[0]
    assert "Adios." in chunks[0]


def test_pack_paragraphs_splits_when_exceeding_max_size():
    paragraphs = ["x" * 100, "y" * 100, "z" * 100]
    chunks = rag._pack_paragraphs(paragraphs, max_size=150, overlap=0)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c) <= 150


def test_pack_paragraphs_ignores_blank_paragraphs():
    paragraphs = ["Contenido real.", "   ", "", "Mas contenido."]
    chunks = rag._pack_paragraphs(paragraphs, max_size=300, overlap=50)
    assert len(chunks) == 1
    assert chunks[0].count("Contenido") >= 1


def test_split_on_words_does_not_break_words():
    text = " ".join(f"palabra{i}" for i in range(60))
    parts = rag._split_on_words(text, max_size=50, overlap=10)
    reconstructed_words = set(" ".join(parts).split())
    original_words = set(text.split())
    assert original_words <= reconstructed_words
    for part in parts:
        # Ninguna parte debe superar max_size salvo que sea una sola
        # palabra mas larga que el limite (caso degenerado no aplicable aqui).
        assert len(part) <= 50


def test_split_on_words_handles_paragraph_longer_than_max_size():
    long_paragraph = "palabra " * 200
    chunks = rag._pack_paragraphs([long_paragraph], max_size=100, overlap=20)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) <= 100


def test_load_and_chunk_documents_tags_domain_and_respects_sections(tmp_path, monkeypatch):
    kb = tmp_path / "kb"
    (kb / "matematicas").mkdir(parents=True)
    (kb / "matematicas" / "algebra.md").write_text(
        "Seccion uno sobre ecuaciones.\n---\nSeccion dos sobre factorizacion.",
        encoding="utf-8",
    )
    (kb / "lenguaje").mkdir(parents=True)
    (kb / "lenguaje" / "gramatica.md").write_text(
        "Seccion sobre sustantivos.",
        encoding="utf-8",
    )
    monkeypatch.setattr(rag, "KB_PATH", str(kb))

    chunks, chunk_domains = rag.load_and_chunk_documents()

    assert len(chunks) == 3
    domain_by_chunk = dict(zip(chunks, chunk_domains))
    assert any("ecuaciones" in c and d == "matematicas" for c, d in zip(chunks, chunk_domains))
    assert any("factorizacion" in c and d == "matematicas" for c, d in zip(chunks, chunk_domains))
    assert any("sustantivos" in c and d == "lenguaje" for c, d in zip(chunks, chunk_domains))


def test_load_and_chunk_documents_empty_kb_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(rag, "KB_PATH", str(tmp_path / "does_not_exist"))
    chunks, chunk_domains = rag.load_and_chunk_documents()
    assert chunks == []
    assert chunk_domains == []
