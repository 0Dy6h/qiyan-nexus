import json

from app.services.network_connectors import TargetPredictionImporter


def test_target_prediction_importer_reads_csv(tmp_path):
    path = tmp_path / "predictions.csv"
    path.write_text(
        "compound,target_symbol,score,source,source_record_id,retrieved_at\n"
        "Astragaloside IV,IL6,0.86,SwissTargetPrediction,swiss-1,2026-06-08T00:00:00Z\n",
        encoding="utf-8",
    )

    result = TargetPredictionImporter(path).load()

    assert len(result.items) == 1
    target = result.items[0]
    assert target.compound == "Astragaloside IV"
    assert target.symbol == "IL6"
    assert target.evidence_type == "predicted"
    assert target.score == 0.86
    assert result.data_sources[0].name == "SwissTargetPrediction"


def test_target_prediction_importer_reads_json(tmp_path):
    path = tmp_path / "predictions.json"
    path.write_text(
        json.dumps(
            [
                {
                    "compound": "Astragaloside IV",
                    "target_symbol": "TNF",
                    "score": 0.72,
                    "source": "SwissTargetPrediction",
                    "source_record_id": "swiss-2",
                    "retrieved_at": "2026-06-08T00:00:00Z",
                }
            ]
        ),
        encoding="utf-8",
    )

    result = TargetPredictionImporter(path).load()

    assert result.items[0].symbol == "TNF"
    assert result.items[0].evidence_type == "predicted"


def test_target_prediction_importer_returns_warning_for_missing_file(tmp_path):
    result = TargetPredictionImporter(tmp_path / "missing.csv").load()

    assert result.items == []
    assert result.warnings == ["Prediction target file is not configured or does not exist."]
