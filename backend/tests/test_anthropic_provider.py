from unittest.mock import MagicMock

from app.schemas.rag import CitationCard
from app.services.llm.anthropic_provider import AnthropicProvider

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


def _make_mock_response(text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


def test_provider_name_remains_anthropic():
    assert AnthropicProvider.name == "anthropic"


def test_generate_answer_calls_client_with_expected_shape():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_mock_response("假回答")
    provider = AnthropicProvider(client=mock_client)

    draft = provider.generate_answer(_QUESTION, _SAMPLE_CITATIONS)

    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args.kwargs

    assert call_kwargs["model"] == "claude-haiku-4-5"
    assert call_kwargs["max_tokens"] == 1024
    assert isinstance(call_kwargs["system"], str)
    assert len(call_kwargs["system"]) > 0
    assert isinstance(call_kwargs["messages"], list)
    assert len(call_kwargs["messages"]) == 1
    user_message = call_kwargs["messages"][0]
    assert user_message["role"] == "user"
    assert isinstance(user_message["content"], str)
    assert _QUESTION in user_message["content"]
    assert _SAMPLE_CITATIONS[0].title in user_message["content"]

    assert draft.text == "假回答"
    assert draft.provider_name == "anthropic"


def test_generate_answer_empty_citations_skips_api():
    mock_client = MagicMock()
    provider = AnthropicProvider(client=mock_client)

    draft = provider.generate_answer(_QUESTION, [])

    mock_client.messages.create.assert_not_called()
    assert "没有检索到足够匹配的证据片段" in draft.text
    assert draft.provider_name == "anthropic"


def test_generate_answer_extracts_text_from_multiple_content_blocks():
    text_block_1 = MagicMock()
    text_block_1.type = "text"
    text_block_1.text = "第一段。"
    non_text_block = MagicMock()
    non_text_block.type = "tool_use"
    text_block_2 = MagicMock()
    text_block_2.type = "text"
    text_block_2.text = "第二段。"

    mock_response = MagicMock()
    mock_response.content = [text_block_1, non_text_block, text_block_2]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    provider = AnthropicProvider(client=mock_client)

    draft = provider.generate_answer(_QUESTION, _SAMPLE_CITATIONS)

    assert draft.text == "第一段。第二段。"
    assert draft.provider_name == "anthropic"
