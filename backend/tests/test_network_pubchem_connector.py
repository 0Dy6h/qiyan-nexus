from app.services.network_connectors import PubChemConnector


def test_pubchem_connector_extracts_cid_from_identifier_list():
    payload = {"IdentifierList": {"CID": [5281605]}}

    identity = PubChemConnector.parse_compound_identity("baicalin", payload)

    assert identity is not None
    assert identity.name == "baicalin"
    assert identity.pubchem_cid == "5281605"
    assert identity.source_record_id == "CID:5281605"


def test_pubchem_connector_returns_none_for_missing_cid():
    assert PubChemConnector.parse_compound_identity("missing", {"IdentifierList": {}}) is None
