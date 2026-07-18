r"""Rank-and-score-blind relevance labeling for the real RAG product path.

The committed seed eval is circular: synthetic documents, questions, expected
IDs, and the deterministic ranker were authored together. This harness instead
freezes held-out questions, runs the citations that ``answer_question`` would
actually show, and emits two separate gitignored files:

* a shuffled reviewer worksheet with no retrieval rank or score;
* a private manifest containing the hidden rank needed for MRR@k.

The reviewer must receive only the worksheet until all ``relevant`` fields are
JSON booleans. The scorer joins labels to the private manifest by candidate ID.
Without complete human labels, no relevance metric is produced. Recall is never
reported because top-k judging does not establish all relevant documents in the
corpus.

Use an isolated real-only runtime. ``seed_pubmed_corpus.py --runtime-root``
creates one without copying the synthetic seed records.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import secrets
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPOSITORY_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

if TYPE_CHECKING:
    from app.repositories.protocols import ChunkRepository, LiteratureRepository

_SCHEMA_VERSION = 2
_DEFAULT_MIN_LIVE_RECORDS = 100

_RELEVANCE_RUBRIC = [
    "标 true：标题/摘要直接提供回答该问题所需的临床或科研证据。",
    "标 false：仅共享宽泛主题、疾病名称或术语，但不能支持回答该问题。",
    "干预问题需区分疗效、安全性和机制；只回答了另一维度时标 false。",
    "摘要信息不足以判断时标 false，并在 reviewer_notes 记录原因。",
    "标注时不得查看 manifest、检索排名、match_score 或算法说明。",
]


def normalize_query_set(payload: Any) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Validate a versioned held-out query set and return normalized entries."""

    metadata: dict[str, Any]
    raw_queries: Any
    if isinstance(payload, dict):
        metadata = {key: value for key, value in payload.items() if key != "queries"}
        raw_queries = payload.get("queries")
    else:
        metadata = {}
        raw_queries = payload

    if not isinstance(raw_queries, list) or not raw_queries:
        raise ValueError("queries must be a non-empty JSON list")

    normalized: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    seen_questions: set[str] = set()
    for index, raw in enumerate(raw_queries, start=1):
        if isinstance(raw, str):
            entry = {
                "query_id": f"q-{index:03d}",
                "question": raw,
                "language": "unspecified",
                "topic": "unspecified",
                "user_role": "unspecified",
                "provenance": "legacy-string-query",
            }
        elif isinstance(raw, dict):
            entry = {
                "query_id": str(raw.get("query_id", "")).strip(),
                "question": str(raw.get("question", "")).strip(),
                "language": str(raw.get("language", "unspecified")).strip(),
                "topic": str(raw.get("topic", "unspecified")).strip(),
                "user_role": str(raw.get("user_role", "unspecified")).strip(),
                "provenance": str(raw.get("provenance", "unspecified")).strip(),
            }
        else:
            raise ValueError(f"query #{index} must be a string or object")

        query_id = entry["query_id"]
        question_key = " ".join(entry["question"].lower().split())
        if not query_id:
            raise ValueError(f"query #{index} has an empty query_id")
        if not question_key:
            raise ValueError(f"query {query_id} has an empty question")
        if query_id in seen_ids:
            raise ValueError(f"duplicate query_id: {query_id}")
        if question_key in seen_questions:
            raise ValueError(f"duplicate question: {entry['question']}")
        seen_ids.add(query_id)
        seen_questions.add(question_key)
        normalized.append(entry)

    metadata.setdefault("dataset_id", "anonymous-held-out-query-set")
    metadata.setdefault("status", "unspecified")
    return metadata, normalized


def _corpus_fingerprint(items: list[Any]) -> str:
    payload = [item.model_dump(mode="json") for item in sorted(items, key=lambda item: item.id)]
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _chunk_fingerprint(chunks: list[Any]) -> str:
    payload = [
        chunk.model_dump(mode="json") for chunk in sorted(chunks, key=lambda chunk: chunk.chunk_id)
    ]
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _query_set_fingerprint(queries: list[dict[str, str]]) -> str:
    canonical = json.dumps(
        queries,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def _candidate_id(
    worksheet_key: str, query_id: str, literature_id: str, retrieval_rank: int
) -> str:
    raw = f"{worksheet_key}|{query_id}|{literature_id}|{retrieval_rank}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _review_payload_fingerprint(candidate: dict[str, Any]) -> str:
    bound_fields = {
        key: candidate.get(key)
        for key in (
            "candidate_id",
            "literature_id",
            "record_origin",
            "title",
            "source",
            "abstract",
            "snippet",
        )
    }
    canonical = json.dumps(bound_fields, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_labeling_bundle(
    query_payload: Any,
    top_k: int,
    *,
    shuffle_seed: str | int | None = None,
    require_real_only: bool = True,
    min_live_records: int = _DEFAULT_MIN_LIVE_RECORDS,
    literature_repository: LiteratureRepository | None = None,
    chunk_repository: ChunkRepository | None = None,
    retrieval_provider_name: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build a blinded worksheet and a separate private retrieval manifest."""

    from app.repositories.runtime_storage import get_chunk_repository, get_literature_repository
    from app.services.rag import answer_question

    if top_k < 1:
        raise ValueError("top_k must be >= 1")
    if min_live_records < 0:
        raise ValueError("min_live_records must be >= 0")

    metadata, queries = normalize_query_set(query_payload)
    literature_repo = literature_repository or get_literature_repository()
    chunk_repo = chunk_repository or get_chunk_repository()
    items = literature_repo.list_items()
    chunks = chunk_repo.list_chunks()
    if not items:
        raise ValueError("validation corpus is empty")

    live_count = sum(item.record_origin == "pubmed_live" for item in items)
    seed_count = sum(item.record_origin == "seed_sample" for item in items)
    non_live_count = len(items) - live_count
    if require_real_only and non_live_count:
        raise ValueError(
            "real-only validation refused: "
            f"found {non_live_count} non-pubmed_live records ({seed_count} seed_sample)"
        )
    if require_real_only:
        live_ids = {item.id for item in items if item.record_origin == "pubmed_live"}
        invalid_chunks = [
            chunk
            for chunk in chunks
            if chunk.literature_id not in live_ids
            or chunk.pdf_upload_id is not None
            or chunk.source_type != "pubmed"
        ]
        if invalid_chunks:
            example = invalid_chunks[0]
            raise ValueError(
                "real-only validation refused: runtime chunk is not a clean PubMed chunk "
                f"({example.chunk_id}, source_type={example.source_type}, "
                f"literature_id={example.literature_id})"
            )
    if live_count < min_live_records:
        raise ValueError(
            f"validation corpus has {live_count} pubmed_live records; "
            f"minimum required is {min_live_records}"
        )

    corpus_sha256 = _corpus_fingerprint(items)
    chunk_sha256 = _chunk_fingerprint(chunks)
    query_set_sha256 = _query_set_fingerprint(queries)
    private_shuffle_secret = (
        str(shuffle_seed) if shuffle_seed is not None else secrets.token_hex(16)
    )
    worksheet_key = hashlib.sha256(
        (
            f"{query_set_sha256}|{corpus_sha256}|{chunk_sha256}|{top_k}|"
            f"{retrieval_provider_name or 'configured-default'}|{private_shuffle_secret}"
        ).encode()
    ).hexdigest()
    worksheet_id = f"rag-blind-{worksheet_key[:16]}"
    items_by_id = {item.id: item for item in items}

    worksheet_queries: list[dict[str, Any]] = []
    manifest_queries: list[dict[str, Any]] = []
    strategies: set[str] = set()
    generated_at = datetime.now(UTC).isoformat()

    for query in queries:
        response = answer_question(
            query["question"],
            top_k=top_k,
            llm_provider_name="deterministic",
            retrieval_provider_name=retrieval_provider_name,
            literature_repository=literature_repo,
            chunk_repository=chunk_repo,
        )
        strategies.add(response.retrieval.strategy)
        visible_candidates: list[dict[str, Any]] = []
        hidden_candidates: list[dict[str, Any]] = []
        for retrieval_rank, citation in enumerate(response.citations, start=1):
            candidate_id = _candidate_id(
                worksheet_key, query["query_id"], citation.literature_id, retrieval_rank
            )
            item = items_by_id.get(citation.literature_id)
            visible_candidates.append(
                {
                    "candidate_id": candidate_id,
                    "literature_id": citation.literature_id,
                    "record_origin": item.record_origin if item is not None else None,
                    "title": citation.title,
                    "source": citation.source,
                    "abstract": item.abstract if item is not None else None,
                    "snippet": citation.snippet,
                    "relevant": None,
                    "reviewer_notes": "",
                }
            )
            hidden_candidates.append(
                {
                    "candidate_id": candidate_id,
                    "literature_id": citation.literature_id,
                    "retrieval_rank": retrieval_rank,
                    "displayed_match_score": citation.match_score,
                    "review_payload_sha256": _review_payload_fingerprint(visible_candidates[-1]),
                }
            )

        random.Random(f"{private_shuffle_secret}:{query['query_id']}").shuffle(visible_candidates)
        worksheet_queries.append({**query, "candidates": visible_candidates})
        manifest_queries.append(
            {
                "query_id": query["query_id"],
                "returned_candidates": len(hidden_candidates),
                "candidates": hidden_candidates,
            }
        )

    strategy = next(iter(strategies)) if len(strategies) == 1 else sorted(strategies)
    worksheet = {
        "schema_version": _SCHEMA_VERSION,
        "worksheet_id": worksheet_id,
        "dataset_id": metadata["dataset_id"],
        "query_set_status": metadata.get("status"),
        "query_set_sha256": query_set_sha256,
        "top_k": top_k,
        "labeling_status": "unlabeled",
        "blinding": (
            "Candidate order is deterministically shuffled. Retrieval rank, displayed "
            "match score, provider configuration, and corpus manifest are kept in a separate "
            "private manifest. Do not give that manifest to the reviewer before labeling."
        ),
        "relevance_rubric": _RELEVANCE_RUBRIC,
        "queries": worksheet_queries,
    }
    manifest = {
        "schema_version": _SCHEMA_VERSION,
        "worksheet_id": worksheet_id,
        "dataset_id": metadata["dataset_id"],
        "top_k": top_k,
        "generated_at": generated_at,
        "git_commit": _git_commit(),
        "query_set": {
            "status": metadata.get("status"),
            "query_count": len(queries),
            "sha256": query_set_sha256,
        },
        "corpus": {
            "size": len(items),
            "pubmed_live_records": live_count,
            "seed_sample_records": seed_count,
            "sha256": corpus_sha256,
            "chunk_count": len(chunks),
            "chunk_sha256": chunk_sha256,
            "literature_ids": sorted(item.id for item in items),
        },
        "retrieval": {
            "strategy": strategy,
            "selection_mode": "rag_answer_citations",
            "top_k": top_k,
            "shuffle_secret": private_shuffle_secret,
            "real_only_required": require_real_only,
            "minimum_live_records": min_live_records,
        },
        "queries": manifest_queries,
    }
    return worksheet, manifest


def _validate_score_inputs(
    worksheet: dict[str, Any], manifest: dict[str, Any]
) -> tuple[int, dict[str, dict[str, Any]]]:
    if worksheet.get("schema_version") != _SCHEMA_VERSION:
        raise ValueError(f"worksheet schema_version must be {_SCHEMA_VERSION}")
    if manifest.get("schema_version") != _SCHEMA_VERSION:
        raise ValueError(f"manifest schema_version must be {_SCHEMA_VERSION}")
    if worksheet.get("worksheet_id") != manifest.get("worksheet_id"):
        raise ValueError("worksheet_id does not match manifest")
    if worksheet.get("dataset_id") != manifest.get("dataset_id"):
        raise ValueError("dataset_id does not match manifest")
    top_k = worksheet.get("top_k")
    if not isinstance(top_k, int) or top_k < 1 or manifest.get("top_k") != top_k:
        raise ValueError("worksheet and manifest must share a positive integer top_k")

    raw_worksheet_queries = worksheet.get("queries")
    query_set = manifest.get("query_set")
    if not isinstance(raw_worksheet_queries, list) or not isinstance(query_set, dict):
        raise ValueError("worksheet queries and manifest query_set are required")
    normalized_queries: list[dict[str, str]] = []
    for entry in raw_worksheet_queries:
        if not isinstance(entry, dict):
            raise ValueError("worksheet query must be an object")
        normalized_queries.append(
            {
                "query_id": str(entry.get("query_id", "")),
                "question": str(entry.get("question", "")),
                "language": str(entry.get("language", "unspecified")),
                "topic": str(entry.get("topic", "unspecified")),
                "user_role": str(entry.get("user_role", "unspecified")),
                "provenance": str(entry.get("provenance", "unspecified")),
            }
        )
    computed_query_sha256 = _query_set_fingerprint(normalized_queries)
    expected_query_sha256 = query_set.get("sha256")
    if (
        not isinstance(expected_query_sha256, str)
        or worksheet.get("query_set_sha256") != expected_query_sha256
        or computed_query_sha256 != expected_query_sha256
        or query_set.get("query_count") != len(normalized_queries)
    ):
        raise ValueError("query-set fingerprint does not match private manifest")

    raw_manifest_queries = manifest.get("queries")
    if not isinstance(raw_manifest_queries, list):
        raise ValueError("manifest queries must be a list")
    manifest_queries: dict[str, dict[str, Any]] = {}
    for entry in raw_manifest_queries:
        query_id = entry.get("query_id") if isinstance(entry, dict) else None
        if not isinstance(query_id, str) or not query_id:
            raise ValueError("manifest query has invalid query_id")
        if query_id in manifest_queries:
            raise ValueError(f"duplicate manifest query_id: {query_id}")
        manifest_queries[query_id] = entry
    return top_k, manifest_queries


def score_worksheet(worksheet: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    """Compute precision@k and MRR@k from complete blinded human labels."""

    top_k, manifest_queries = _validate_score_inputs(worksheet, manifest)
    worksheet_queries = worksheet.get("queries")
    if not isinstance(worksheet_queries, list):
        raise ValueError("worksheet queries must be a list")

    per_query: list[dict[str, Any]] = []
    precisions: list[float] = []
    reciprocal_ranks: list[float] = []
    unlabeled = 0
    seen_query_ids: set[str] = set()
    returned_counts: list[int] = []

    for entry in worksheet_queries:
        if not isinstance(entry, dict):
            raise ValueError("worksheet query must be an object")
        query_id = entry.get("query_id")
        if not isinstance(query_id, str) or not query_id:
            raise ValueError("worksheet query has invalid query_id")
        if query_id in seen_query_ids:
            raise ValueError(f"duplicate worksheet query_id: {query_id}")
        seen_query_ids.add(query_id)
        manifest_entry = manifest_queries.get(query_id)
        if manifest_entry is None:
            raise ValueError(f"query {query_id} is missing from manifest")

        candidates = entry.get("candidates")
        hidden_candidates = manifest_entry.get("candidates")
        if not isinstance(candidates, list) or not isinstance(hidden_candidates, list):
            raise ValueError(f"query {query_id} candidates must be lists")
        returned_counts.append(len(candidates))

        hidden_by_id: dict[str, dict[str, Any]] = {}
        ranks: set[int] = set()
        for hidden in hidden_candidates:
            candidate_id = hidden.get("candidate_id") if isinstance(hidden, dict) else None
            rank = hidden.get("retrieval_rank") if isinstance(hidden, dict) else None
            if not isinstance(candidate_id, str) or not candidate_id:
                raise ValueError(f"query {query_id} has invalid manifest candidate_id")
            if candidate_id in hidden_by_id:
                raise ValueError(f"query {query_id} has duplicate manifest candidate_id")
            if not isinstance(rank, int) or rank < 1 or rank > top_k or rank in ranks:
                raise ValueError(f"query {query_id} has invalid retrieval_rank")
            payload_sha256 = hidden.get("review_payload_sha256")
            if not isinstance(payload_sha256, str) or not payload_sha256:
                raise ValueError(f"query {query_id} is missing review payload fingerprint")
            hidden_by_id[candidate_id] = hidden
            ranks.add(rank)

        labels_by_id: dict[str, bool | None] = {}
        for candidate in candidates:
            candidate_id = candidate.get("candidate_id") if isinstance(candidate, dict) else None
            if not isinstance(candidate_id, str) or not candidate_id:
                raise ValueError(f"query {query_id} has invalid worksheet candidate_id")
            if candidate_id in labels_by_id:
                raise ValueError(f"query {query_id} has duplicate worksheet candidate_id")
            relevant = candidate.get("relevant")
            if relevant is not None and not isinstance(relevant, bool):
                raise ValueError(
                    f"query {query_id} candidate {candidate_id} relevant must be a JSON boolean"
                )
            labels_by_id[candidate_id] = relevant
            if _review_payload_fingerprint(candidate) != hidden_by_id.get(candidate_id, {}).get(
                "review_payload_sha256"
            ):
                raise ValueError(
                    f"query {query_id} candidate {candidate_id} review payload was modified"
                )

        if set(labels_by_id) != set(hidden_by_id):
            raise ValueError(f"query {query_id} candidate IDs do not match manifest")
        if any(label is None for label in labels_by_id.values()):
            unlabeled += 1
            continue

        relevant_ranks = sorted(
            hidden_by_id[candidate_id]["retrieval_rank"]
            for candidate_id, relevant in labels_by_id.items()
            if relevant is True
        )
        precision = len(relevant_ranks) / top_k
        first_rank = relevant_ranks[0] if relevant_ranks else None
        reciprocal = 1.0 / first_rank if first_rank is not None else 0.0
        precisions.append(precision)
        reciprocal_ranks.append(reciprocal)
        per_query.append(
            {
                "query_id": query_id,
                "question": entry.get("question"),
                "returned_candidates": len(candidates),
                "precision_at_k": round(precision, 3),
                "first_relevant_rank": first_rank,
                "reciprocal_rank_at_k": round(reciprocal, 3),
            }
        )

    extra_manifest_queries = set(manifest_queries) - seen_query_ids
    if extra_manifest_queries:
        raise ValueError(
            f"manifest has queries missing from worksheet: {sorted(extra_manifest_queries)}"
        )

    labeled = len(precisions)
    total_queries = len(worksheet_queries)
    complete = unlabeled == 0 and labeled == total_queries
    return {
        "worksheet_id": worksheet.get("worksheet_id"),
        "top_k": top_k,
        "total_queries": total_queries,
        "labeled_queries": labeled,
        "unlabeled_queries": unlabeled,
        "queries_returning_full_k": sum(count == top_k for count in returned_counts),
        "queries_returning_zero": sum(count == 0 for count in returned_counts),
        "mean_returned_candidates": (
            round(sum(returned_counts) / total_queries, 3) if total_queries else None
        ),
        "mean_precision_at_k": (
            round(sum(precisions) / labeled, 3) if complete and labeled else None
        ),
        "mrr_at_k": (round(sum(reciprocal_ranks) / labeled, 3) if complete and labeled else None),
        "note": (
            "Top-k human labels support precision@k and MRR@k only. Recall, untruncated "
            "MRR, nDCG, and clinical usefulness are not established by this worksheet."
        ),
        "per_query": per_query if complete else [],
    }


def _manifest_output_path(worksheet_path: Path) -> Path:
    return worksheet_path.with_name(f"{worksheet_path.stem}.manifest{worksheet_path.suffix}")


def _cmd_build(args: argparse.Namespace) -> int:
    query_payload = json.loads(Path(args.queries).read_text(encoding="utf-8"))
    try:
        worksheet, manifest = build_labeling_bundle(
            query_payload,
            max(1, args.top_k),
            shuffle_seed=args.shuffle_seed,
            require_real_only=not args.allow_mixed_corpus,
            min_live_records=max(0, args.min_live_records),
            retrieval_provider_name=args.retrieval_provider,
        )
    except ValueError as exc:
        print(f"Refused to build worksheet: {exc}")
        return 2

    out_path = Path(args.out)
    manifest_path = (
        Path(args.manifest_out) if args.manifest_out else _manifest_output_path(out_path)
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(worksheet, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Wrote blinded worksheet: {out_path} "
        f"({len(worksheet['queries'])} queries, top_k={worksheet['top_k']})."
    )
    print(
        f"Wrote private manifest: {manifest_path} "
        f"({manifest['corpus']['pubmed_live_records']}/{manifest['corpus']['size']} live records)."
    )
    print("Give only the worksheet to the reviewer. Keep the manifest private until labeling ends.")
    return 0


def _cmd_score(args: argparse.Namespace) -> int:
    worksheet = json.loads(Path(args.worksheet).read_text(encoding="utf-8"))
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    try:
        result = score_worksheet(worksheet, manifest)
    except ValueError as exc:
        print(f"Refused to score worksheet: {exc}")
        return 2
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    print(rendered)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered + "\n", encoding="utf-8")
    if result["unlabeled_queries"]:
        print(
            f"\n{result['unlabeled_queries']} query(ies) still unlabeled; metrics remain partial."
        )
        return 3
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    build_parser = sub.add_parser("build", help="Generate blinded worksheet + private manifest.")
    build_parser.add_argument("--queries", required=True, help="Versioned held-out query JSON.")
    build_parser.add_argument("--out", required=True, help="Blinded worksheet output path.")
    build_parser.add_argument("--manifest-out", help="Private manifest output path.")
    build_parser.add_argument("--top-k", type=int, default=5, help="Candidates per query.")
    build_parser.add_argument(
        "--shuffle-seed",
        help=(
            "Optional deterministic shuffle seed for diagnostics. Omit for a private random "
            "Track A blinding secret."
        ),
    )
    build_parser.add_argument(
        "--min-live-records",
        type=int,
        default=_DEFAULT_MIN_LIVE_RECORDS,
        help="Fail if the runtime contains fewer pubmed_live records (default 100).",
    )
    build_parser.add_argument(
        "--allow-mixed-corpus",
        action="store_true",
        help="Allow non-pubmed_live records (diagnostics only; not Track A baseline).",
    )
    build_parser.add_argument(
        "--retrieval-provider",
        choices=("keyword", "vector", "hybrid"),
        help="Explicit provider; Track A baseline uses keyword.",
    )
    build_parser.set_defaults(func=_cmd_build)

    score_parser = sub.add_parser("score", help="Score a fully labeled blinded worksheet.")
    score_parser.add_argument("--worksheet", required=True, help="Filled blinded worksheet.")
    score_parser.add_argument("--manifest", required=True, help="Private retrieval manifest.")
    score_parser.add_argument("--out", help="Optional metrics JSON output path.")
    score_parser.set_defaults(func=_cmd_score)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
