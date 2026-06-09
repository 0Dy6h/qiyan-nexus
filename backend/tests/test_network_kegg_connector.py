from app.services.network_connectors import KeggConnector


def test_kegg_connector_parses_link_and_list_payloads():
    link_text = "hsa:3569\tpath:hsa04668\nhsa:7124\tpath:hsa04668\n"
    list_text = "path:hsa04668\tTNF signaling pathway - Homo sapiens (human)\n"

    pathways = KeggConnector.parse_pathways(link_text, list_text)

    assert len(pathways) == 1
    pathway = pathways[0]
    assert pathway.term_id == "hsa04668"
    assert pathway.name == "TNF signaling pathway"
    assert pathway.genes == ["3569", "7124"]
    assert pathway.source_record_id == "path:hsa04668"
