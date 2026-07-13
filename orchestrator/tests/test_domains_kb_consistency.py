"""
Verifica que la configuracion de dominios (domains.py) y las carpetas reales
de knowledge_base/ no se hayan desincronizado. Sin esto, es facil agregar una
carpeta de asignatura y olvidar registrar sus keywords/label (o viceversa).
"""
import os

import domains

KB_PATH = os.path.join(os.path.dirname(__file__), "..", "knowledge_base")


def _kb_domain_folders():
    if not os.path.isdir(KB_PATH):
        return set()
    return {d for d in os.listdir(KB_PATH) if os.path.isdir(os.path.join(KB_PATH, d))}


def test_every_kb_folder_has_keywords_and_label():
    kb_domains = _kb_domain_folders()
    missing_keywords = kb_domains - set(domains.DOMAIN_KEYWORDS.keys())
    missing_labels = kb_domains - set(domains.DOMAIN_LABELS.keys())
    assert not missing_keywords, f"Carpetas en knowledge_base/ sin keywords en domains.py: {missing_keywords}"
    assert not missing_labels, f"Carpetas en knowledge_base/ sin label en domains.py: {missing_labels}"


def test_keyword_domains_and_labels_match():
    assert set(domains.DOMAIN_KEYWORDS.keys()) == set(domains.DOMAIN_LABELS.keys())


def test_every_domain_has_at_least_one_keyword():
    for domain, keywords in domains.DOMAIN_KEYWORDS.items():
        assert len(keywords) > 0, f"Dominio sin keywords: {domain}"
