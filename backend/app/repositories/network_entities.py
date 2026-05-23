import json
from pathlib import Path
from typing import Any

from app.schemas.network_entities import (
    Compound,
    CompoundTargetPathway,
    Formula,
    Herb,
    Pathway,
    Target,
)

_DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "network"


def _read_json(path: Path) -> list[dict[str, Any]]:
    raw: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
    return raw


class NetworkEntityRepository:
    """Read-only repository over the network-pharmacology seed JSON files.

    Files live under backend/data/network/. Seed data is small and immutable,
    so we cache parsed lists at module level. Tests can pass a custom data_root
    to point at a fixture directory; otherwise the production seed is used.
    """

    def __init__(self, data_root: Path | None = None):
        self.data_root = data_root or _DATA_ROOT

    def list_herbs(self) -> list[Herb]:
        return [
            Herb.model_validate(item) for item in _read_json(self.data_root / "sample_herbs.json")
        ]

    def list_formulas(self) -> list[Formula]:
        return [
            Formula.model_validate(item)
            for item in _read_json(self.data_root / "sample_formulas.json")
        ]

    def list_compounds(self) -> list[Compound]:
        return [
            Compound.model_validate(item)
            for item in _read_json(self.data_root / "sample_compounds.json")
        ]

    def list_targets(self) -> list[Target]:
        return [
            Target.model_validate(item)
            for item in _read_json(self.data_root / "sample_targets.json")
        ]

    def list_pathways(self) -> list[Pathway]:
        return [
            Pathway.model_validate(item)
            for item in _read_json(self.data_root / "sample_pathways.json")
        ]

    def list_chains(self) -> list[CompoundTargetPathway]:
        return [
            CompoundTargetPathway.model_validate(item)
            for item in _read_json(self.data_root / "sample_chains.json")
        ]

    def find_formula_by_query(self, query: str) -> Formula | None:
        normalized = query.strip().lower()
        for formula in self.list_formulas():
            if formula.name == query.strip() or formula.pinyin.lower() == normalized:
                return formula
        return None

    def find_herb_by_query(self, query: str) -> Herb | None:
        normalized = query.strip().lower()
        for herb in self.list_herbs():
            if herb.name == query.strip() or herb.pinyin.lower() == normalized:
                return herb
        return None
