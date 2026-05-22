from app.schemas.rag import CitationCard
from app.services.llm.provider import (
    AnswerDraft,
    DeterministicProvider,
    MockClaudeProvider,
    select_provider,
)

_SAMPLE_CITATIONS: list[CitationCard] = [
    CitationCard(
        literature_id="pmid-40100001",
        title="Atopic dermatitis, skin barrier dysfunction, and immune pathways",
        source="PubMed curated AD sample",
        snippet="Reviewing barrier disruption and Th2 skewing.",
        reason="skin_barrier, immune_pathway",
        confidence=0.74,
    ),
    CitationCard(
        literature_id="cn-ad-guideline-004",
        title="特应性皮炎中西医结合诊疗专家共识中的证据要点",
        source="CNKI curated AD sample",
        snippet="提炼共识中关于分型辨证、屏障修复与长期管理的关键证据。",
        reason="guideline, clinical_management",
        confidence=0.86,
    ),
]

_QUESTION = "特应性皮炎肠-脑-皮肤轴的证据有哪些？"


def test_deterministic_provider_keeps_existing_text_markers():
    provider = DeterministicProvider()
    draft = provider.generate_answer(_QUESTION, _SAMPLE_CITATIONS)

    assert isinstance(draft, AnswerDraft)
    assert draft.provider_name == "deterministic"
    assert "deterministic retrieval" in draft.text
    assert "屏障" in draft.text
    assert "引用来源" in draft.text


def test_deterministic_provider_falls_back_when_no_citations():
    provider = DeterministicProvider()
    draft = provider.generate_answer(_QUESTION, [])

    assert draft.provider_name == "deterministic"
    assert "没有检索到足够匹配的证据片段" in draft.text


def test_mock_claude_provider_marks_text_with_mock_prefix():
    provider = MockClaudeProvider()
    draft = provider.generate_answer(_QUESTION, _SAMPLE_CITATIONS)

    assert draft.provider_name == "mock_claude"
    assert draft.text.startswith("【模拟 Claude 草稿】")
    assert "deterministic retrieval" not in draft.text


def test_mock_claude_provider_includes_question_and_citation_titles():
    provider = MockClaudeProvider()
    draft = provider.generate_answer(_QUESTION, _SAMPLE_CITATIONS)

    assert _QUESTION in draft.text
    assert "Atopic dermatitis, skin barrier dysfunction" in draft.text


def test_mock_claude_provider_handles_empty_citations():
    provider = MockClaudeProvider()
    draft = provider.generate_answer(_QUESTION, [])

    assert draft.provider_name == "mock_claude"
    assert "暂无可引用的证据片段" in draft.text


def test_select_provider_default_is_deterministic(monkeypatch):
    monkeypatch.delenv("QIYAN_LLM_PROVIDER", raising=False)
    provider = select_provider()
    assert provider.name == "deterministic"


def test_select_provider_returns_mock_claude_when_env_set(monkeypatch):
    monkeypatch.setenv("QIYAN_LLM_PROVIDER", "mock_claude")
    provider = select_provider()
    assert provider.name == "mock_claude"


def test_select_provider_is_case_insensitive(monkeypatch):
    monkeypatch.setenv("QIYAN_LLM_PROVIDER", "Mock_Claude")
    provider = select_provider()
    assert provider.name == "mock_claude"


def test_select_provider_falls_back_for_invalid_value(monkeypatch):
    monkeypatch.setenv("QIYAN_LLM_PROVIDER", "definitely-not-a-provider")
    provider = select_provider()
    assert provider.name == "deterministic"


def test_select_provider_falls_back_for_empty_env(monkeypatch):
    monkeypatch.setenv("QIYAN_LLM_PROVIDER", "")
    provider = select_provider()
    assert provider.name == "deterministic"


def test_select_provider_accepts_explicit_name_overriding_env(monkeypatch):
    monkeypatch.setenv("QIYAN_LLM_PROVIDER", "mock_claude")
    provider = select_provider("deterministic")
    assert provider.name == "deterministic"
