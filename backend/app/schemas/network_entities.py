from typing import Literal

from pydantic import BaseModel, Field


class Herb(BaseModel):
    id: str
    name: str
    pinyin: str
    latin_name: str | None = None
    category: str | None = None
    evidence_tags: list[str] = Field(default_factory=list)


class Formula(BaseModel):
    id: str
    name: str
    pinyin: str
    indication_tags: list[str] = Field(default_factory=list)
    herb_ids: list[str] = Field(default_factory=list)
    summary: str | None = None


class Compound(BaseModel):
    id: str
    name: str
    english_name: str | None = None
    pubchem_cid: str | None = None
    herb_ids: list[str] = Field(default_factory=list)


class Target(BaseModel):
    id: str
    symbol: str
    name: str
    uniprot_id: str | None = None
    disease_ids: list[str] = Field(default_factory=list)


class Pathway(BaseModel):
    id: str
    name: str
    kegg_id: str | None = None
    category: str | None = None
    target_ids: list[str] = Field(default_factory=list)


class CompoundTargetPathway(BaseModel):
    """Denormalized seed edge: one compound -> one target -> one pathway -> disease.

    Score is a static curated value (not computed). Used by network analysis
    chain construction so the service layer does not need to join 4 tables.
    """

    compound_id: str
    target_id: str
    pathway_id: str
    disease: str
    score: float = Field(ge=0, le=1)


EntityKind = Literal["herb", "formula", "compound", "target", "pathway"]
