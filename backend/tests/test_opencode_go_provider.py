import json
import logging

import httpx

from app.core.config import get_settings
from app.schemas.rag import CitationCard
from app.services.llm.opencode_go_provider import OpenCodeGoProvider

_QUESTION = "特应性皮炎肠-脑-皮肤轴的证据有哪些？"
_SAMPLE_CITATIONS: list[CitationCard] = [
    CitationCard(
        literature_id="cn-ad-gbs-001",
        title="肠-脑-皮肤轴与特应性皮炎中医证候研究",
        source="CNKI curated AD sample",
        snippet="围绕特应性皮炎、肠-脑-皮肤轴与中医证候关联进行综述。",
        quote="肠-脑-皮肤轴视角讨论特应性皮炎的中医证候演变。",
        reason="gut_skin_axis, tcm_syndrome",
        confidence=0.86,
    )
]


def test_provider_name_remains_opencode_go():
    assert OpenCodeGoProvider.name == "opencode_go"


def test_empty_citations_skip_http_request(monkeypatch):
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={})

    provider = OpenCodeGoProvider(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    draft = provider.generate_answer(_QUESTION, [])

    assert called is False
    assert draft.provider_name == "opencode_go"
    assert "没有检索到足够匹配的证据片段" in draft.text


def test_missing_api_key_falls_back_without_http_request(monkeypatch):
    monkeypatch.delenv("QIYAN_OPENCODE_GO_API_KEY", raising=False)
    get_settings.cache_clear()
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={})

    provider = OpenCodeGoProvider(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    draft = provider.generate_answer(_QUESTION, _SAMPLE_CITATIONS)

    assert called is False
    assert draft.provider_name == "deterministic"
    assert "deterministic retrieval" in draft.text
    get_settings.cache_clear()


def test_generate_answer_posts_chat_completion_and_extracts_usage(monkeypatch):
    monkeypatch.setenv("QIYAN_OPENCODE_GO_API_KEY", "test-secret")
    monkeypatch.setenv("QIYAN_OPENCODE_GO_BASE_URL", "https://example.test/v1/")
    monkeypatch.setenv("QIYAN_OPENCODE_GO_MODEL", "deepseek-v4-flash")
    monkeypatch.setenv("QIYAN_OPENCODE_GO_MAX_TOKENS", "128")
    monkeypatch.setenv("QIYAN_OPENCODE_GO_TEMPERATURE", "0.4")
    get_settings.cache_clear()
    seen_request: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_request["url"] = str(request.url)
        seen_request["authorization"] = request.headers.get("Authorization")
        seen_request["body"] = request.read().decode("utf-8")
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "OpenCode Go 证据综述回答"}}],
                "usage": {"prompt_tokens": 123, "completion_tokens": 45},
            },
        )

    provider = OpenCodeGoProvider(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    draft = provider.generate_answer(_QUESTION, _SAMPLE_CITATIONS)

    assert seen_request["url"] == "https://example.test/v1/chat/completions"
    assert seen_request["authorization"] == "Bearer test-secret"
    body = str(seen_request["body"])
    assert '"model":"deepseek-v4-flash"' in body
    assert '"max_tokens":128' in body
    assert '"temperature":0.4' in body
    payload = json.loads(body)
    system_content = payload["messages"][0]["content"]
    user_content = payload["messages"][1]["content"]
    assert _QUESTION in body
    assert _SAMPLE_CITATIONS[0].title in body
    assert _SAMPLE_CITATIONS[0].snippet in body
    assert _SAMPLE_CITATIONS[0].quote in body
    assert "[1]" not in user_content
    assert "引用 1" in user_content
    assert "证据ID：cn-ad-gbs-001" in user_content
    assert "只输出 JSON" in system_content
    assert '"claims"' in system_content
    assert '"text"' in system_content
    assert '"evidence_refs"' in system_content
    assert "不得使用未提供的证据 ID" in system_content
    assert "每条 claim" in system_content
    assert "输出 2-4 条短中文证据句" in system_content
    assert "不要输出标题、参考文献列表" in system_content
    assert "不要使用数字序号方括号引用" in system_content
    assert "不要带免责声明" in system_content
    assert draft.text == "OpenCode Go 证据综述回答"
    assert draft.provider_name == "opencode_go"
    assert draft.input_tokens == 123
    assert draft.output_tokens == 45
    get_settings.cache_clear()


def test_http_error_falls_back_and_does_not_log_secret(monkeypatch, caplog):
    monkeypatch.setenv("QIYAN_OPENCODE_GO_API_KEY", "secret-that-must-not-leak")
    get_settings.cache_clear()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "bad key"})

    caplog.set_level(logging.WARNING)
    provider = OpenCodeGoProvider(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    draft = provider.generate_answer(_QUESTION, _SAMPLE_CITATIONS)

    assert draft.provider_name == "deterministic"
    assert "OpenCodeGoProvider falling back to deterministic" in caplog.text
    assert "secret-that-must-not-leak" not in caplog.text
    assert "Authorization" not in caplog.text
    get_settings.cache_clear()


def test_empty_message_content_falls_back(monkeypatch):
    monkeypatch.setenv("QIYAN_OPENCODE_GO_API_KEY", "test-secret")
    monkeypatch.setenv("QIYAN_OPENCODE_GO_BASE_URL", "https://example.test/v1/")
    get_settings.cache_clear()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": None}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 0},
            },
        )

    provider = OpenCodeGoProvider(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    draft = provider.generate_answer(_QUESTION, _SAMPLE_CITATIONS)

    assert draft.provider_name == "deterministic"
    assert "deterministic retrieval" in draft.text
    assert draft.input_tokens is None
    assert draft.output_tokens is None
    get_settings.cache_clear()
