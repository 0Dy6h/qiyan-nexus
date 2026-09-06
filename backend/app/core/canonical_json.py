"""Canonical JSON serialization shared across layers.

``qiyan_canonical_json_v1``: ``json.dumps`` with ``ensure_ascii=False``,
``sort_keys=True`` and ``separators=(",", ":")``, hashed with SHA-256. The
assembly-plan service and every network-task repository backend must agree
byte-for-byte on this function, otherwise write-time and consume-time
recomputation of bound hashes diverge. The offline independent validators
(``backend/scripts/validate_*.py``) intentionally keep their own zero-shared
copies of the same rule.
"""

import hashlib
import json
from typing import Any


def canonical_json_payload(payload: Any) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_json_sha256(payload: Any) -> str:
    return hashlib.sha256(canonical_json_payload(payload).encode("utf-8")).hexdigest()
