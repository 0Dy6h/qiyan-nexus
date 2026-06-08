"""Protocol definitions for repository interfaces.

These protocols enable dependency inversion: services depend on the
abstract interface, not the concrete InMemory/SQLite implementation.
"""

from typing import Any, Protocol

from app.schemas.chunk import LiteratureChunk
from app.schemas.literature import LiteratureItem, PdfParseResult
from app.schemas.network import (
    AnalysisType,
    DataMode,
    NetworkAnalysisResult,
    NetworkTaskRecord,
    TaskStatus,
)


class LiteratureRepository(Protocol):
    def list_items(self) -> list[LiteratureItem]: ...

    def get_item_by_id(self, item_id: str) -> LiteratureItem | None: ...

    def update_pdf_metadata(
        self,
        literature_id: str,
        pdf_upload_id: str,
        pdf_file_name: str,
        pdf_parse_status: str,
    ) -> LiteratureItem | None: ...

    def update_pdf_parse_status(
        self,
        literature_id: str,
        pdf_parse_status: str,
        pdf_parse_message: str | None = None,
        pdf_parse_started_at: str | None = None,
        pdf_parse_finished_at: str | None = None,
        pdf_parse_result: PdfParseResult | None = None,
        last_parse_trigger: str | None = None,
    ) -> LiteratureItem | None: ...

    def bulk_upsert_pubmed_items(self, incoming_items: list[dict[str, Any]]) -> tuple[int, int]: ...


class ChunkRepository(Protocol):
    def list_chunks(self) -> list[LiteratureChunk]: ...

    def list_chunks_by_literature_id(self, literature_id: str) -> list[LiteratureChunk]: ...

    def get_chunk_by_id(self, chunk_id: str) -> LiteratureChunk | None: ...

    def upsert_uploaded_pdf_chunk(
        self,
        chunk_id: str,
        literature_id: str,
        pdf_upload_id: str,
        text: str,
        source_quote: str,
        evidence_tags: list[str],
        related_entity_ids: list[str] | None = None,
    ) -> LiteratureChunk: ...


class NetworkTaskRepositoryProtocol(Protocol):
    def read_all(self) -> list[NetworkTaskRecord]: ...

    def get(self, task_id: str) -> NetworkTaskRecord | None: ...

    def upsert(
        self,
        task_id: str,
        query: str,
        analysis_type: AnalysisType,
        status: TaskStatus,
        progress: int,
        poll_count: int,
        result: NetworkAnalysisResult | None,
        created_at: str,
        data_mode: DataMode = "mock",
        error: str | None = None,
        warnings: list[str] | None = None,
    ) -> NetworkTaskRecord: ...
