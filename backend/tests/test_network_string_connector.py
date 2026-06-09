from app.services.network_connectors import StringConnector


def test_string_connector_parses_network_tsv():
    text = "preferredName_A\tpreferredName_B\tscore\nIL6\tTNF\t0.982\nIL6\tSTAT3\t0.821\n"

    edges = StringConnector.parse_network_tsv(text)

    assert len(edges) == 2
    assert edges[0].source == "IL6"
    assert edges[0].target == "TNF"
    assert edges[0].score == 0.982
    assert edges[0].source_record_id == "STRING:IL6-TNF"
