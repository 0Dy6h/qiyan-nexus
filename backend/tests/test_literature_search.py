from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.repositories.literature import InMemoryLiteratureRepository


def _seed_one_pdf_upload(monkeypatch, tmp_path: Path) -> None:
    """Bootstrap an isolated runtime fixture and attach a fake PDF to cn-ad-gbs-001."""
    from app.services import literature as literature_service

    original_path = (
        Path(__file__).resolve().parents[1] / "data" / "literature" / "sample_ad_literature.json"
    )
    temp_path = tmp_path / "sample_ad_literature.json"
    temp_path.write_text(original_path.read_text(encoding="utf-8"), encoding="utf-8")

    monkeypatch.setattr(
        literature_service,
        "_REPOSITORY",
        InMemoryLiteratureRepository(temp_path),
    )
    client = TestClient(app)
    response = client.post(
        "/api/literature/pdf-metadata",
        json={
            "literature_id": "cn-ad-gbs-001",
            "file_name": "ad-evidence.pdf",
            "source_type": "uploaded_pdf",
        },
    )
    assert response.status_code == 200


def test_literature_search_returns_curated_results_for_keyword():
    client = TestClient(app)

    response = client.get("/api/literature/search", params={"q": "特应性皮炎"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "特应性皮炎"
    assert payload["total"] == 20
    assert payload["page"] == 1
    assert payload["page_size"] == 10
    assert payload["total_pages"] == 2
    assert payload["sort"] == "relevance"
    assert payload["items"][0]["id"] == "cn-ad-gbs-001"
    assert payload["items"][0]["authors"] == ["王琳", "张倩", "刘晨"]
    assert payload["items"][0]["evidence_tags"] == ["gut_skin_axis", "tcm_syndrome", "skin_barrier"]
    assert payload["items"][0]["citation_url"] == "https://example.org/cnki/cn-ad-gbs-001"
    assert payload["items"][0]["pdf_upload_id"] is None
    assert payload["items"][0]["pdf_file_name"] is None
    assert payload["items"][0]["pdf_parse_status"] is None


def test_literature_search_prioritizes_pubmed_results_for_english_keyword():
    client = TestClient(app)

    response = client.get("/api/literature/search", params={"q": "atopic dermatitis"})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"][:3]] == [
        "pmid-40100001",
        "pmid-40100002",
        "pmid-40100003",
    ]


def test_literature_search_filters_source():
    client = TestClient(app)

    response = client.get(
        "/api/literature/search",
        params={"q": "特应性皮炎", "source": "pubmed"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 10
    assert [item["source_type"] for item in response.json()["items"]] == ["pubmed"] * 10


def test_literature_search_returns_empty_results_for_unknown_keyword():
    client = TestClient(app)

    response = client.get("/api/literature/search", params={"q": "完全不存在关键词 xyz"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 0
    assert payload["total_pages"] == 0
    assert payload["items"] == []


def test_literature_search_accepts_pagination_and_sort_params():
    client = TestClient(app)

    response = client.get(
        "/api/literature/search",
        params={"q": "特应性皮炎", "page": 2, "page_size": 5, "sort": "year_asc"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["page"] == 2
    assert payload["page_size"] == 5
    assert payload["total"] == 20
    assert payload["total_pages"] == 4
    assert payload["sort"] == "year_asc"
    assert len(payload["items"]) == 5
    assert [item["year"] for item in payload["items"]] == sorted(
        item["year"] for item in payload["items"]
    )


def test_literature_search_rejects_invalid_page_size():
    client = TestClient(app)

    response = client.get(
        "/api/literature/search",
        params={"q": "特应性皮炎", "page_size": 0},
    )

    assert response.status_code == 422


def test_literature_search_rejects_invalid_source():
    client = TestClient(app)

    response = client.get(
        "/api/literature/search",
        params={"q": "特应性皮炎", "source": "unknown"},
    )

    assert response.status_code == 422


def test_literature_search_requires_non_empty_query():
    client = TestClient(app)

    response = client.get("/api/literature/search", params={"q": ""})

    assert response.status_code == 422


def test_literature_search_filters_to_items_with_pdf_upload_when_has_pdf_upload_true(
    monkeypatch, tmp_path: Path
):
    _seed_one_pdf_upload(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.get(
        "/api/literature/search",
        params={"q": "特应性皮炎", "has_pdf_upload": "true"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert [item["id"] for item in payload["items"]] == ["cn-ad-gbs-001"]
    assert payload["items"][0]["pdf_upload_id"] == "pdf-cn-ad-gbs-001-ad-evidence-pdf"


def test_literature_search_excludes_items_with_pdf_upload_when_has_pdf_upload_false(
    monkeypatch, tmp_path: Path
):
    _seed_one_pdf_upload(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.get(
        "/api/literature/search",
        params={"q": "特应性皮炎", "has_pdf_upload": "false"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 19
    assert "cn-ad-gbs-001" not in [item["id"] for item in payload["items"]]


def test_literature_search_ignores_pdf_filter_when_param_omitted(monkeypatch, tmp_path: Path):
    _seed_one_pdf_upload(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.get("/api/literature/search", params={"q": "特应性皮炎"})

    assert response.status_code == 200
    assert response.json()["total"] == 20
