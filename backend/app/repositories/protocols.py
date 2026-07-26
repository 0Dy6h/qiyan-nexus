"""Protocol definitions for repository interfaces.

These protocols enable dependency inversion: services depend on the
abstract interface, not the concrete InMemory/SQLite implementation.
"""

from collections.abc import Callable
from typing import Any, Protocol

from app.schemas.chunk import LiteratureChunk
from app.schemas.literature import LiteratureItem, PdfParseResult
from app.schemas.network import (
    AnalysisType,
    DataMode,
    NetworkAnalysisResult,
    NetworkCompoundTargetSnapshot,
    NetworkDiseaseTargetSnapshot,
    NetworkResearchProtocol,
    NetworkTargetAdjudication,
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

    def create(self, record: NetworkTaskRecord) -> bool: ...

    def get(self, task_id: str) -> NetworkTaskRecord | None: ...

    def get_owned(self, task_id: str, owner_id: str) -> NetworkTaskRecord | None: ...

    def list_records_for_owner(self, owner_id: str) -> list[NetworkTaskRecord]:
        """Return records owned by ``owner_id``, newest first.

        Legacy ownerless records (``owner_id is None``) never match — listing
        fails closed just like ``get_owned``. Ordering is deterministic:
        ``created_at`` descending, ties broken by ``task_id`` descending.
        """
        ...

    def advance(
        self,
        task_id: str,
        owner_id: str,
        transition: Callable[[NetworkTaskRecord], NetworkTaskRecord],
    ) -> NetworkTaskRecord | None: ...

    def append_adjudication(
        self,
        task_id: str,
        owner_id: str,
        adjudication: NetworkTargetAdjudication,
    ) -> NetworkTaskRecord | None:
        """Append one adjudication to the owned task and return the record.

        Append-only: existing adjudications are never reordered, updated, or
        removed.  Fails closed (returns ``None``) for unknown, foreign, or
        legacy ownerless records, mirroring ``get_owned``/``advance``.
        """
        ...

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
        research_protocol: NetworkResearchProtocol | None = None,
        disease_target_import: NetworkDiseaseTargetSnapshot | None = None,
        compound_target_import: NetworkCompoundTargetSnapshot | None = None,
        source_task_id: str | None = None,
        owner_id: str = "local-preview",
        data_mode: DataMode = "mock",
        error: str | None = None,
        warnings: list[str] | None = None,
    ) -> NetworkTaskRecord: ...
