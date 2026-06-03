from app.schemas.rag import CitationCard

GROUNDING_SYSTEM_PROMPT = (
    "你是特应性皮炎（AD）证据综述助理。"
    "输出必须严格基于提供的引用片段；不得编造引用之外的事实。"
    "输出 1-3 条短中文证据句，但只输出 JSON。"
    'JSON 顶层必须是对象，且只包含 "claims" 数组；'
    '每条 claim 必须包含 "text" 字符串和 "evidence_refs" 字符串数组。'
    "每条 claim 只能引用一个证据ID，且 evidence_refs 必须只包含该证据ID。"
    "每条 claim 只能由该证据ID对应的证据文本直接蕴含。"
    "不要跨引用综合，不要把多个证据片段合并成一条 claim。"
    "不要添加引用片段没有明示的治疗疗效、靶点、生活质量、因果或指南地位。"
    "不得使用未提供的证据 ID。"
    "不要使用数字序号方括号引用，例如 [1] 或 [2]。"
    "不要输出标题、参考文献列表；不要输出 Markdown 或 JSON 之外的说明文字。"
    "保持中文学术风格。不要带免责声明。"
)


def build_citation_text(citations: list[CitationCard]) -> str:
    blocks: list[str] = []
    for index, citation in enumerate(citations, 1):
        parts = [
            f"引用 {index}",
            f"证据ID：{citation.chunk_id or citation.literature_id}",
            f"标题（元数据）：{citation.title}",
            f"来源（元数据）：{citation.source}",
        ]
        if citation.quote:
            parts.append(f"片段摘要（元数据）：{citation.snippet}")
            parts.append(f"证据文本（claim 只能基于此字段）：{citation.quote.strip()}")
        else:
            parts.append(f"证据文本（claim 只能基于此字段）：{citation.snippet}")
        if citation.reason:
            parts.append(f"匹配依据（元数据）：{citation.reason}")
        parts.append(f"置信度（元数据）：{citation.confidence:.2f}")
        parts.append(f"文献ID（元数据）：{citation.literature_id}")
        blocks.append("\n".join(parts))
    return "\n\n".join(blocks)
