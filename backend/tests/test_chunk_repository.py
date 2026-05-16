import json
from pathlib import Path

from app.repositories.chunk import InMemoryChunkRepository

SAMPLE_CHUNKS = [
    {
        "chunk_id": "chunk-cn-ad-gbs-001-abstract",
        "literature_id": "cn-ad-gbs-001",
        "section": "abstract",
        "text": "文章从肠-脑-皮肤轴视角讨论特应性皮炎的中医证候演变。",
        "source_quote": "肠-脑-皮肤轴视角讨论特应性皮炎的中医证候演变。",
        "evidence_tags": ["gut_skin_axis", "tcm_syndrome"],
        "related_entity_ids": ["disease:atopic-dermatitis", "pathway:gut-skin-axis"],
    },
    {
        "chunk_id": "chunk-pmid-40100001-review",
        "literature_id": "pmid-40100001",
        "section": "review",
        "text": "This review summarizes barrier disruption and type 2 inflammation in AD.",
        "source_quote": "barrier disruption and type 2 inflammation in AD",
        "evidence_tags": ["skin_barrier", "immune_pathway"],
        "related_entity_ids": ["disease:atopic-dermatitis", "pathway:type-2-inflammation"],
    },
]


def write_sample_data(path: Path, items: list[dict]) -> None:
    path.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")


def test_chunk_repository_loads_all_chunks_from_json(tmp_path: Path):
    data_path = tmp_path / "sample_ad_chunks.json"
    write_sample_data(data_path, SAMPLE_CHUNKS)

    chunks = InMemoryChunkRepository(data_path).list_chunks()

    assert [chunk.chunk_id for chunk in chunks] == [
        "chunk-cn-ad-gbs-001-abstract",
        "chunk-pmid-40100001-review",
    ]


def test_chunk_repository_filters_by_literature_id(tmp_path: Path):
    data_path = tmp_path / "sample_ad_chunks.json"
    write_sample_data(data_path, SAMPLE_CHUNKS)

    chunks = InMemoryChunkRepository(data_path).list_chunks_by_literature_id("cn-ad-gbs-001")

    assert len(chunks) == 1
    assert chunks[0].section == "abstract"
    assert chunks[0].evidence_tags == ["gut_skin_axis", "tcm_syndrome"]


def test_chunk_repository_get_chunk_by_id_returns_matching_chunk(tmp_path: Path):
    data_path = tmp_path / "sample_ad_chunks.json"
    write_sample_data(data_path, SAMPLE_CHUNKS)

    chunk = InMemoryChunkRepository(data_path).get_chunk_by_id("chunk-pmid-40100001-review")

    assert chunk is not None
    assert chunk.literature_id == "pmid-40100001"
    assert chunk.related_entity_ids == ["disease:atopic-dermatitis", "pathway:type-2-inflammation"]


def test_chunk_repository_returns_none_for_unknown_chunk_id(tmp_path: Path):
    data_path = tmp_path / "sample_ad_chunks.json"
    write_sample_data(data_path, SAMPLE_CHUNKS)

    assert InMemoryChunkRepository(data_path).get_chunk_by_id("unknown") is None


def test_chunk_repository_upserts_uploaded_pdf_chunk(tmp_path: Path):
    data_path = tmp_path / "sample_ad_chunks.json"
    write_sample_data(data_path, SAMPLE_CHUNKS)

    repository = InMemoryChunkRepository(data_path)
    chunk = repository.upsert_uploaded_pdf_chunk(
        chunk_id="chunk-pdf-cn-ad-gbs-001-ad-evidence-pdf-uploaded",
        literature_id="cn-ad-gbs-001",
        pdf_upload_id="pdf-cn-ad-gbs-001-ad-evidence-pdf",
        text="上传 PDF ad-evidence.pdf 已完成解析，包含特应性皮炎证据片段。",
        source_quote="包含特应性皮炎证据片段",
        evidence_tags=["uploaded_pdf", "pdf_parse"],
    )

    assert chunk.source_type == "uploaded_pdf"
    assert chunk.pdf_upload_id == "pdf-cn-ad-gbs-001-ad-evidence-pdf"
    assert repository.get_chunk_by_id("chunk-pdf-cn-ad-gbs-001-ad-evidence-pdf-uploaded") == chunk

    repository.upsert_uploaded_pdf_chunk(
        chunk_id="chunk-pdf-cn-ad-gbs-001-ad-evidence-pdf-uploaded",
        literature_id="cn-ad-gbs-001",
        pdf_upload_id="pdf-cn-ad-gbs-001-ad-evidence-pdf",
        text="上传 PDF ad-evidence.pdf 已重新解析，包含 RAG 引用片段。",
        source_quote="包含 RAG 引用片段",
        evidence_tags=["uploaded_pdf", "pdf_parse"],
    )

    persisted_chunks = repository.list_chunks_by_literature_id("cn-ad-gbs-001")
    uploaded_chunks = [item for item in persisted_chunks if item.source_type == "uploaded_pdf"]
    assert len(uploaded_chunks) == 1
    assert uploaded_chunks[0].source_quote == "包含 RAG 引用片段"
