"""
Tests del enrutador semantico. Descargan el modelo de embeddings la primera
vez que corren (requiere conexion a internet en CI/dev; en el contenedor
Docker ya viene pre-descargado, ver Dockerfile).
"""
from router import route_query


def test_route_query_picks_relevant_domain():
    result = route_query(
        "Mi process en VHDL tiene rising_edge y sensitivity list con std_logic_vector"
    )
    assert result["domain"] == "vhdl"


def test_route_query_confidence_lower_for_unrelated_text():
    on_topic = route_query(
        "VHDL process sensitivity list rising_edge std_logic_vector synchronous counter"
    )
    off_topic = route_query("Receta de galletas de chocolate con harina y azucar")
    assert off_topic["confidence"] < on_topic["confidence"]


def test_route_query_scores_include_all_domains():
    result = route_query("cualquier consulta")
    assert set(result["scores"].keys()) == {"vhdl", "rf", "network"}
