from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.seed_pubmed_corpus import prepare_isolated_runtime, validate_real_only_corpus


def test_prepare_isolated_runtime_creates_empty_json_state(tmp_path: Path):
    literature_path, chunk_path = prepare_isolated_runtime(tmp_path / "validation")

    assert literature_path.read_text(encoding="utf-8") == "[]\n"
    assert chunk_path.read_text(encoding="utf-8") == "[]\n"


def test_prepare_isolated_runtime_refuses_to_reuse_without_resume(tmp_path: Path):
    runtime_root = tmp_path / "validation"
    prepare_isolated_runtime(runtime_root)

    with pytest.raises(ValueError, match="already exists"):
        prepare_isolated_runtime(runtime_root)


def test_validate_real_only_corpus_rejects_seed_and_too_small_corpus():
    with pytest.raises(ValueError, match="seed_sample"):
        validate_real_only_corpus(
            [
                SimpleNamespace(record_origin="pubmed_live"),
                SimpleNamespace(record_origin="seed_sample"),
            ],
            min_live_records=1,
        )

    with pytest.raises(ValueError, match="minimum required is 2"):
        validate_real_only_corpus(
            [SimpleNamespace(record_origin="pubmed_live")], min_live_records=2
        )
