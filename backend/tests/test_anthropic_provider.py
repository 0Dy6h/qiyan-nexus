import logging
from unittest.mock import MagicMock

import pytest
from anthropic import APIError, APITimeoutError, AuthenticationError, RateLimitError

from app.schemas.rag import CitationCard
from app.services.llm.anthropic_provider import AnthropicProvider
from app.services.llm.provider import AnswerDraft, DeterministicProvider

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


def test_fallback_on_authentication_error():
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = AuthenticationError(
        message="401 invalid key", response=MagicMock(), body=None
    )
    mock_fallback = MagicMock()
    mock_fallback.name = "deterministic"
    mock_fallback.generate_answer.return_value = AnswerDraft(
        text="FALLBACK_TEXT", provider_name="deterministic"
    )
    provider = AnthropicProvider(client=mock_client, fallback=mock_fallback)

    draft = provider.generate_answer(_QUESTION, _SAMPLE_CITATIONS)

    mock_fallback.generate_answer.assert_called_once_with(_QUESTION, _SAMPLE_CITATIONS)
    assert draft.text == "FALLBACK_TEXT"
    assert draft.provider_name == "deterministic"


def test_fallback_on_rate_limit_error():
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = RateLimitError(
        message="429 too many requests", response=MagicMock(), body=None
    )
    mock_fallback = MagicMock()
    mock_fallback.name = "deterministic"
    mock_fallback.generate_answer.return_value = AnswerDraft(
        text="FALLBACK_TEXT", provider_name="deterministic"
    )
    provider = AnthropicProvider(client=mock_client, fallback=mock_fallback)

    draft = provider.generate_answer(_QUESTION, _SAMPLE_CITATIONS)

    mock_fallback.generate_answer.assert_called_once_with(_QUESTION, _SAMPLE_CITATIONS)
    assert draft.text == "FALLBACK_TEXT"
    assert draft.provider_name == "deterministic"


def test_fallback_on_api_timeout_error():
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = APITimeoutError(request=MagicMock())
    mock_fallback = MagicMock()
    mock_fallback.name = "deterministic"
    mock_fallback.generate_answer.return_value = AnswerDraft(
        text="FALLBACK_TEXT", provider_name="deterministic"
    )
    provider = AnthropicProvider(client=mock_client, fallback=mock_fallback)

    draft = provider.generate_answer(_QUESTION, _SAMPLE_CITATIONS)

    mock_fallback.generate_answer.assert_called_once_with(_QUESTION, _SAMPLE_CITATIONS)
    assert draft.text == "FALLBACK_TEXT"
    assert draft.provider_name == "deterministic"


def test_fallback_on_generic_api_error():
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = APIError(
        message="generic api error", request=MagicMock(), body=None
    )
    mock_fallback = MagicMock()
    mock_fallback.name = "deterministic"
    mock_fallback.generate_answer.return_value = AnswerDraft(
        text="FALLBACK_TEXT", provider_name="deterministic"
    )
    provider = AnthropicProvider(client=mock_client, fallback=mock_fallback)

    draft = provider.generate_answer(_QUESTION, _SAMPLE_CITATIONS)

    mock_fallback.generate_answer.assert_called_once_with(_QUESTION, _SAMPLE_CITATIONS)
    assert draft.text == "FALLBACK_TEXT"
    assert draft.provider_name == "deterministic"


def test_non_anthropic_exception_propagates():
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = ValueError("boom")
    mock_fallback = MagicMock()
    mock_fallback.name = "deterministic"
    mock_fallback.generate_answer.return_value = AnswerDraft(
        text="FALLBACK_TEXT", provider_name="deterministic"
    )
    provider = AnthropicProvider(client=mock_client, fallback=mock_fallback)

    with pytest.raises(ValueError, match="boom"):
        provider.generate_answer(_QUESTION, _SAMPLE_CITATIONS)

    mock_fallback.generate_answer.assert_not_called()


def test_default_fallback_is_deterministic():
    provider = AnthropicProvider(client=MagicMock())

    assert isinstance(provider._fallback, DeterministicProvider)  # type: ignore[arg-type]


def test_missing_anthropic_api_key_falls_back_before_client_call(monkeypatch, caplog):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from app.core.config import get_settings

    get_settings.cache_clear()
    mock_fallback = MagicMock()
    mock_fallback.name = "deterministic"
    mock_fallback.generate_answer.return_value = AnswerDraft(
        text="FALLBACK_TEXT", provider_name="deterministic"
    )
    caplog.set_level(logging.WARNING)
    try:
        provider = AnthropicProvider(fallback=mock_fallback)

        draft = provider.generate_answer(_QUESTION, _SAMPLE_CITATIONS)
    finally:
        get_settings.cache_clear()

    mock_fallback.generate_answer.assert_called_once_with(_QUESTION, _SAMPLE_CITATIONS)
    assert draft.text == "FALLBACK_TEXT"
    assert draft.provider_name == "deterministic"
    assert "missing API key" in caplog.text


def test_anthropic_auth_resolution_type_error_falls_back(caplog):
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = TypeError(
        "Could not resolve authentication method. Expected api_key or auth_token."
    )
    mock_fallback = MagicMock()
    mock_fallback.name = "deterministic"
    mock_fallback.generate_answer.return_value = AnswerDraft(
        text="FALLBACK_TEXT", provider_name="deterministic"
    )
    caplog.set_level(logging.WARNING)
    provider = AnthropicProvider(client=mock_client, fallback=mock_fallback)

    draft = provider.generate_answer(_QUESTION, _SAMPLE_CITATIONS)

    mock_fallback.generate_answer.assert_called_once_with(_QUESTION, _SAMPLE_CITATIONS)
    assert draft.text == "FALLBACK_TEXT"
    assert draft.provider_name == "deterministic"
    assert "TypeError" in caplog.text


def test_non_auth_type_error_propagates():
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = TypeError("unexpected local bug")
    mock_fallback = MagicMock()
    mock_fallback.name = "deterministic"
    mock_fallback.generate_answer.return_value = AnswerDraft(
        text="FALLBACK_TEXT", provider_name="deterministic"
    )
    provider = AnthropicProvider(client=mock_client, fallback=mock_fallback)

    with pytest.raises(TypeError, match="unexpected local bug"):
        provider.generate_answer(_QUESTION, _SAMPLE_CITATIONS)

    mock_fallback.generate_answer.assert_not_called()


def test_settings_override_model_and_max_tokens(monkeypatch):
    monkeypatch.setenv("QIYAN_ANTHROPIC_MODEL", "claude-opus-test")
    monkeypatch.setenv("QIYAN_ANTHROPIC_MAX_TOKENS", "2048")
    from app.core.config import get_settings

    get_settings.cache_clear()
    try:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_mock_response("override test")
        provider = AnthropicProvider(client=mock_client)
        provider.generate_answer(_QUESTION, _SAMPLE_CITATIONS)

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-opus-test"
        assert call_kwargs["max_tokens"] == 2048
    finally:
        get_settings.cache_clear()


def test_default_settings_model_and_max_tokens():
    from app.core.config import get_settings

    get_settings.cache_clear()
    try:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_mock_response("default test")
        provider = AnthropicProvider(client=mock_client)
        provider.generate_answer(_QUESTION, _SAMPLE_CITATIONS)

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-haiku-4-5"
        assert call_kwargs["max_tokens"] == 1024
    finally:
        get_settings.cache_clear()


def test_token_usage_extracted_from_response():
    mock_response = _make_mock_response("token test")
    mock_usage = MagicMock()
    mock_usage.input_tokens = 123
    mock_usage.output_tokens = 456
    mock_response.usage = mock_usage

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    provider = AnthropicProvider(client=mock_client)

    draft = provider.generate_answer(_QUESTION, _SAMPLE_CITATIONS)

    assert draft.input_tokens == 123
    assert draft.output_tokens == 456


def test_token_usage_none_when_usage_missing():
    mock_response = _make_mock_response("no usage")
    mock_response.usage = None

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    provider = AnthropicProvider(client=mock_client)

    draft = provider.generate_answer(_QUESTION, _SAMPLE_CITATIONS)

    assert draft.input_tokens is None
    assert draft.output_tokens is None


def test_fallback_draft_has_none_tokens():
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = APIError(
        message="error", request=MagicMock(), body=None
    )
    mock_fallback = MagicMock()
    mock_fallback.name = "deterministic"
    mock_fallback.generate_answer.return_value = AnswerDraft(
        text="FALLBACK_TEXT", provider_name="deterministic"
    )
    provider = AnthropicProvider(client=mock_client, fallback=mock_fallback)

    draft = provider.generate_answer(_QUESTION, _SAMPLE_CITATIONS)

    assert draft.input_tokens is None
    assert draft.output_tokens is None


def _make_auth_error():
    return AuthenticationError(message="401 invalid key", response=MagicMock(), body=None)


def _make_rate_limit_error():
    return RateLimitError(message="429 too many requests", response=MagicMock(), body=None)


def _make_timeout_error():
    return APITimeoutError(request=MagicMock())


def _make_generic_api_error():
    return APIError(message="generic api error", request=MagicMock(), body=None)


@pytest.mark.parametrize(
    "error_factory,error_type_name",
    [
        (_make_auth_error, "AuthenticationError"),
        (_make_rate_limit_error, "RateLimitError"),
        (_make_timeout_error, "APITimeoutError"),
        (_make_generic_api_error, "APIError"),
    ],
)
def test_fallback_logs_warning_with_error_type_and_message(caplog, error_factory, error_type_name):
    caplog.set_level(logging.WARNING)
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = error_factory()
    mock_fallback = MagicMock()
    mock_fallback.name = "deterministic"
    mock_fallback.generate_answer.return_value = AnswerDraft(
        text="fallback", provider_name="deterministic"
    )
    provider = AnthropicProvider(client=mock_client, fallback=mock_fallback)

    provider.generate_answer(_QUESTION, _SAMPLE_CITATIONS)

    assert "AnthropicProvider falling back to deterministic" in caplog.text
    assert error_type_name in caplog.text
