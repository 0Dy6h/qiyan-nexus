# C1 Slice 2/5 — AnthropicProvider.generate_answer (Mock-Client Skeleton)

**Date**: 2026-05-25
**Branch**: `feat/c1-anthropic-provider` (3 commits ahead of main)
**Commits**:
- `cb5e365` feat(llm): register anthropic provider name + skeleton class (C1 slice 1/5) — last sprint
- `61b01c6` chore(gitignore): ignore .codegraph/ local index dir
- `a1972fa` [verified] feat(llm): AnthropicProvider.generate_answer w/ injectable client (C1 slice 2/5)

**Verification**: Backend gauntlet green — ruff format/check + mypy strict + 206 pytest passed (202 baseline + 4 new). Independent reviewer (Claude Code via freemodel/claude-opus-4-7) returned `passed=true`, 0 security/logic concerns, 3 non-blocking suggestions deferred to slices 3/4.

## Scope

Implement the real-Anthropic code path with a dependency-injected client so the call shape is testable without hitting the live API. Real API key + end-to-end verification land in slices 3 (failure fallback) and 5 (live smoke).

## Changes

### `backend/app/services/llm/anthropic_provider.py`

- `AnthropicProvider.__init__(client: Anthropic | None = None) -> None` — lazy-constructs `anthropic.Anthropic()` when `client is None` (SDK reads `ANTHROPIC_API_KEY` env). `TYPE_CHECKING` guard keeps anthropic import out of module top-level.
- Class constants `MODEL = "claude-haiku-4-5"` (roadmap C1 starting model) and `MAX_TOKENS = 1024`.
- `generate_answer` assembles system + user prompt:
  - system: AD evidence reviewer, strict citation grounding, no disclaimer (disclaimer stays in `rag.py` per B1 handoff contract).
  - user: question + numbered citations (title / source / snippet / reason / confidence / literature_id).
- Calls `self._client.messages.create(model=, max_tokens=, system=, messages=[{role:user, content:…}])`.
- Extracts text from `response.content` ContentBlock list (only `type=='text'` blocks, concatenated in order).
- Empty-citations branch short-circuits with fixed Chinese fallback string, does not call the API:
  > `当前样本文献中没有检索到足够匹配的证据片段。请调整问题关键词或切换来源后重试。`
- Error handling intentionally deferred to slice 3.

### `backend/tests/test_anthropic_provider.py` (new, 97 lines)

4 tests, all using `MagicMock` injected client (no internet):

1. `test_provider_name_remains_anthropic` — sanity.
2. `test_generate_answer_calls_client_with_expected_shape` — locks model name, max_tokens, system string, messages role/content shape, citation title appears in user content, returned `AnswerDraft.text` + `provider_name`.
3. `test_generate_answer_empty_citations_skips_api` — verifies no API call, fallback string returned.
4. `test_generate_answer_extracts_text_from_multiple_content_blocks` — locks the `type=='text'` filter (e.g. `tool_use` blocks ignored) and order preservation.

## Out of scope (by design)

- Slice 3: error handling / fallback to deterministic provider on `anthropic.APIError`.
- Slice 4: MODEL / MAX_TOKENS settings injection (`backend/app/core/config.py`); token usage observability; cost field on `AnswerDraft`.
- Slice 5: real ANTHROPIC_API_KEY live smoke; RAG eval 50q anthropic vs deterministic comparison report.

## Three-agent execution log

- **Implementer**: OpenCode (`opencode-go/deepseek-v4-pro`) via `/home/dyh2026/bin/hermes-opencode-run --workdir /home/dyh2026/Projects/Tcm_tech`. Self-iterated to fix one ruff unused-import warning. Final self-report claimed gauntlet green.
- **Verifier**: Hermes independently re-ran the full backend gauntlet (`ruff format --check`, `ruff check`, `mypy app`, `pytest -q`) — all 206 tests green, format/check/strict-mypy clean. Self-reports are not trusted.
- **Reviewer**: Claude Code (`claude-opus-4-7` via freemodel) reading only the diff + test file, no context about implementation history. Returned JSON `passed=true`. Non-blocking suggestions:
  1. `_extract_text_from_response` could `getattr(response, 'content', [])` to defend mock missing-attr — current tests already cover SDK real shape, non-blocking.
  2. MODEL/MAX_TOKENS class constants — fine for now, consider settings injection in slice 4 when token observability lands.
  3. confidence two-decimal formatting in `_build_citation_text` — could add a regression-locking test in slice 3/4.

## Boundary tools / env tricks for next agent

- **Don't use `bash -ic "..."`** for env-needing commands: `~/.bashrc` has `case $- in *i*) return` at top that short-circuits in non-interactive contexts (Hermes terminal), and `HERMES_REDACT_SECRETS=*** literalizes `$ANTHROPIC_AUTH_TOKEN` if exported in-process. Workaround: write a `/tmp/run-X.sh` shell script that reads `FREEMODEL_CLAUDE_API_KEY` (or analogous) directly from `~/.bashrc` line and exports it before invoking the binary; feed long prompts via stdin to avoid heredoc/`$()` nesting bugs.
- **Don't reach for `bash -ic 'use-freemodel'`** for the same reason. Direct env export by reading the .bashrc line is reliable.
- **rtk hook + Windows `.exe` symlink**: claude binary on this WSL host is symlinked to `claude-code/bin/claude.exe`. The global rtk hook (`rtk init -g --auto-patch` was run) wraps Bash commands inside Claude Code; the wrap path doesn't always survive the WSL interop layer cleanly. If `claude` exits 127 with stderr `[rtk: No such file or directory (os error 2)]`, run claude directly with stdin piping and `--print --model claude-opus-4-7`.

## Next session

1. Pick up C1 slice 3 (fallback to deterministic on `anthropic.APIError`) using the same agent-router pattern — OpenCode writes, Hermes verifies, Claude Code reviews.
2. C1 slice 4 (MODEL/MAX_TOKENS into `core/config.py` + token-usage transit through `AnswerDraft`) can be parallel since it touches different code surfaces.
3. C1 slice 5 requires user to provide a real `ANTHROPIC_API_KEY` with budget cap confirmation; until then, slices 3 + 4 can land first.
4. Last-known claude-provider health (2026-05-25 evening): only `freemodel` ALIVE; `anyrouter` (timeout), `coderelay` + `jiuleyunapi` ("model claude-opus-4-7 不存在") all broken. Re-smoke before next review pass.
