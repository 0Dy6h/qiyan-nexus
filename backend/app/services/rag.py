import re
from pathlib import Path

from app.repositories.chunk import InMemoryChunkRepository
from app.repositories.literature import InMemoryLiteratureRepository
from app.schemas.chunk import LiteratureChunk
from app.schemas.literature import LiteratureItem, LiteratureSource
from app.schemas.rag import CitationCard, RagAnswerResponse, RetrievalMetadata
from app.services.literature import detect_query_language

DISCLAIMER = "非诊断结论、需结合临床。"
_SAMPLE_DATA_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "literature" / "sample_ad_literature.json"
)
_CHUNK_DATA_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "literature" / "sample_ad_chunks.json"
)
_REPOSITORY = InMemoryLiteratureRepository(_SAMPLE_DATA_PATH)
_CHUNK_REPOSITORY = InMemoryChunkRepository(_CHUNK_DATA_PATH)
_CONFIDENCE_BY_SOURCE_TYPE = {
    "cn_literature": 0.86,
    "pubmed": 0.74,
}

_KEYWORD_ALIASES = {
    "gut": ["肠", "肠道", "gut", "microbiome", "菌群"],
    "skin_barrier": ["屏障", "barrier", "filaggrin"],
    "immune": ["免疫", "inflammation", "immune", "th2", "jak", "cytokine"],
    "pruritus": ["瘙痒", "itch", "il-31"],
    "formula": ["复方", "方剂", "formula", "herbal"],
    "network": ["网络药理学", "network pharmacology", "靶点", "通路", "target", "pathway"],
    "pediatric": ["儿童", "pediatric"],
}

_EVIDENCE_TAG_TOPIC_CN: dict[str, str] = {
    "skin_barrier": "皮肤屏障",
    "filaggrin": "丝聚蛋白与皮肤屏障",
    "gut_skin_axis": "肠-皮肤轴",
    "microbiome": "肠道菌群与皮肤微生物",
    "immune_pathway": "免疫通路与细胞因子信号",
    "pathway": "信号通路与细胞因子调控",
    "neuroimmune": "神经免疫",
    "pruritus": "瘙痒",
    "formula": "中药复方",
    "network_pharmacology": "网络药理学线索",
    "tcm_syndrome": "中医证候辨证",
    "guideline": "诊疗共识与皮肤屏障维护",
    "clinical_management": "长期临床管理",
    "review": "证据综述",
    "pathogenesis": "发病机制",
    "severity": "严重度关联",
    "flare": "急性发作",
    "targeted_therapy": "靶向治疗",
    "systematic_review": "系统综述",
    "pediatric": "儿童分层",
    "uploaded_pdf": "上传 PDF 解析片段",
    "pdf_parse": "PDF 解析",
    "atopic_dermatitis": "特应性皮炎主题",
}


def tokenize_query(question: str) -> list[str]:
    normalized = question.lower().strip()
    tokens = set(re.findall(r"[a-z0-9\-]+", normalized))
    for alias, keywords in _KEYWORD_ALIASES.items():
        if any(keyword in normalized for keyword in keywords):
            tokens.add(alias)
    for char in normalized:
        if "\u4e00" <= char <= "\u9fff":
            tokens.add(char)
    return sorted(tokens)


def score_item(item: LiteratureItem, chunk: LiteratureChunk | None, query_tokens: list[str]) -> int:
    haystacks = [
        item.title.lower(),
        item.snippet.lower(),
        (item.abstract or "").lower(),
        " ".join(item.keywords).lower(),
        " ".join(item.evidence_tags).lower(),
        chunk.text.lower() if chunk else "",
        " ".join(chunk.evidence_tags).lower() if chunk else "",
    ]
    score = 0
    for token in query_tokens:
        if any(token in haystack for haystack in haystacks if haystack):
            score += 1
    return score


def _collect_topic_phrases(citations: list[CitationCard]) -> list[str]:
    seen: list[str] = []
    for citation in citations:
        if not citation.reason:
            continue
        for raw in citation.reason.split(","):
            tag = raw.strip()
            phrase = _EVIDENCE_TAG_TOPIC_CN.get(tag)
            if phrase and phrase not in seen:
                seen.append(phrase)
    return seen


def _alias_tag_bonus(tags: list[str], query_tokens: list[str], weight: int) -> int:
    if not tags:
        return 0
    matched = 0
    for token in query_tokens:
        if token in _KEYWORD_ALIASES and any(token in tag for tag in tags):
            matched += 1
    return matched * weight


def build_answer(citations: list[CitationCard]) -> str:
    if not citations:
        return "当前样本文献中没有检索到足够匹配的证据片段。请调整问题关键词或切换来源后重试。"

    top_reasons = [citation.reason for citation in citations if citation.reason]
    top_reasons_text = "；".join(top_reasons[:2]) if top_reasons else "当前命中的证据片段"
    titles = "；".join(citation.title for citation in citations[:2])
    topics = _collect_topic_phrases(citations)
    topics_text = "、".join(topics) if topics else "暂无主题映射"
    return (
        f"基于当前检索到的证据片段，已优先返回与问题最相关的文献。"
        f"主要证据线索包括：{top_reasons_text}。"
        f"代表性文献：{titles}。"
        f"涉及的研究主题：{topics_text}。"
        f"请结合引用来源逐条核对，相关结论仍属非诊断结论、需结合临床。"
        f"此回答仍是基于样本文献的 deterministic retrieval 结果，用于验证引用卡片、证据片段与合规文案。"
    )


def answer_question(
    question: str, source: LiteratureSource = "all", top_k: int = 2
) -> RagAnswerResponse:
    normalized_question = question.strip()
    preferred_source_type = (
        "cn_literature" if detect_query_language(normalized_question) == "zh" else "pubmed"
    )
    query_tokens = tokenize_query(normalized_question)

    items = _REPOSITORY.list_items()
    if source != "all":
        items = [item for item in items if item.source_type == source]

    ranked_items: list[tuple[int, int, LiteratureItem, LiteratureChunk | None]] = []
    for item in items:
        chunks: list[LiteratureChunk | None] = list(
            _CHUNK_REPOSITORY.list_chunks_by_literature_id(item.id)
        )
        if not chunks:
            chunks = [None]
        for chunk in chunks:
            score = score_item(item, chunk, query_tokens)
            score += _alias_tag_bonus(item.evidence_tags, query_tokens, 2)
            if chunk:
                score += _alias_tag_bonus(chunk.evidence_tags, query_tokens, 7)
            language_bonus = 1 if item.source_type == preferred_source_type else 0
            ranked_items.append((score, language_bonus, item, chunk))

    ranked_items.sort(key=lambda row: (row[1], row[0], row[2].year), reverse=True)
    available_citation_count = sum(1 for score, _, _, _ in ranked_items if score > 0)
    if available_citation_count == 0:
        available_citation_count = len(ranked_items)

    selected = [row for row in ranked_items if row[0] > 0][:top_k]
    if not selected:
        selected = ranked_items[:top_k]

    if (
        top_k >= 3
        and source == "all"
        and len(selected) == top_k
        and all(row[1] == 1 for row in selected)
    ):
        cross_chunk = next(
            (
                row
                for row in ranked_items
                if row[0] > 0 and row[1] == 0 and row[3] is not None and row not in selected
            ),
            None,
        )
        if cross_chunk is not None:
            selected = selected[:-1] + [cross_chunk]

    citations = []
    for _, _, item, chunk in selected:
        chunk_tags = chunk.evidence_tags if chunk and chunk.evidence_tags else []
        reason_tags = chunk_tags or item.evidence_tags
        citations.append(
            CitationCard(
                literature_id=item.id,
                chunk_id=chunk.chunk_id if chunk else None,
                title=item.title,
                source=item.source,
                snippet=item.snippet,
                quote=chunk.source_quote if chunk else None,
                reason=(", ".join(reason_tags[:2]) if reason_tags else None),
                confidence=_CONFIDENCE_BY_SOURCE_TYPE[item.source_type],
            )
        )

    return RagAnswerResponse(
        question=normalized_question,
        answer=build_answer(citations),
        disclaimer=DISCLAIMER,
        retrieval=RetrievalMetadata(
            applied_source=source,
            applied_top_k=top_k,
            available_citation_count=available_citation_count,
        ),
        citations=citations,
    )
