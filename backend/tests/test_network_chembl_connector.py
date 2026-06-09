from app.services.network_connectors import ChemblConnector, CompoundCandidate, CompoundIdentity


def test_chembl_connector_extracts_known_activity_targets():
    compound = CompoundCandidate(name="baicalin", herb="黄芩")
    identity = CompoundIdentity(name="baicalin", pubchem_cid="5281605")
    payload = {
        "activities": [
            {
                "target_pref_name": "Interleukin-6",
                "target_chembl_id": "CHEMBL1827",
                "target_organism": "Homo sapiens",
                "standard_value": "12.5",
                "standard_units": "nM",
                "pchembl_value": "7.9",
                "assay_chembl_id": "CHEMBLASSAY1",
            },
            {
                "target_pref_name": "Mouse target",
                "target_chembl_id": "CHEMBL999",
                "target_organism": "Mus musculus",
            },
        ]
    }

    targets = ChemblConnector.parse_activity_targets(compound, identity, payload)

    assert len(targets) == 1
    assert targets[0].compound == "baicalin"
    assert targets[0].symbol == "Interleukin-6"
    assert targets[0].evidence_type == "known_activity"
    assert targets[0].source_record_id == "CHEMBLASSAY1"
    assert targets[0].score == 0.79
