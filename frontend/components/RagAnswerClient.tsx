"use client";

import { FormEvent, useState } from "react";
import { useSearchParams } from "next/navigation";

import {
  answerRagQuestion,
  CitationCard,
  getRagSourceLabel,
  GroundingMetadata,
  ProviderSli,
  RagAnswerResponse,
  RagSource,
} from "../lib/api/rag";
import { buildPdfDownloadUrl } from "../lib/api/literature";
import { buildAnswerMarkdown, buildAnswerMarkdownFileName } from "../lib/rag-export";
import { getCitationEmptyCopy, getEmptyStateCopy, getStatusCopy } from "../lib/ui/states";
import { getSurfaceCardStyle, getSurfaceSectionStyle } from "../lib/ui/surfaces";
import { CardBodyText, CardMetaRow } from "./CardMeta";
import EntityChips from "./EntityChips";
import StatusPanel from "./StatusPanel";

type RagState = {
  question: string;
  source: RagSource;
  topK: number;
  result: RagAnswerResponse | null;
  error: string | null;
  isLoading: boolean;
};

function formatConfidence(value: number) {
  return `${Math.round(value * 100)}%`;
}

function formatTokenUsage(value: number | null | undefined) {
  return value == null ? "未返回" : `${value}`;
}

function formatLatencyMs(sli: ProviderSli | null | undefined) {
  return sli?.provider_latency_ms == null ? "未返回" : `${sli.provider_latency_ms} ms`;
}

function formatEstimatedCost(sli: ProviderSli | null | undefined) {
  return sli?.estimated_cost_usd == null ? "未估算" : `$${sli.estimated_cost_usd.toFixed(6)}`;
}

function formatGroundingCoverage(grounding: GroundingMetadata) {
  return `${grounding.cited_claim_count}/${grounding.claim_count}`;
}

function formatStructuredClaimCount(grounding: GroundingMetadata) {
  return `${grounding.structured_claims.length}`;
}

function formatNativeGrounding(grounding: GroundingMetadata) {
  return grounding.provider_native_grounding ? "true" : "false";
}

function formatGroundingTool(grounding: GroundingMetadata) {
  return grounding.tool_name ?? "无";
}

function formatSemanticThreshold(grounding: GroundingMetadata) {
  return grounding.semantic_threshold == null ? "未启用" : grounding.semantic_threshold.toFixed(2);
}

function formatSemanticScore(grounding: GroundingMetadata) {
  return grounding.min_semantic_score == null
    ? "未计算"
    : `${Math.round(grounding.min_semantic_score * 100)}%`;
}

function formatNliThreshold(grounding: GroundingMetadata) {
  return grounding.nli_threshold == null ? "未启用" : grounding.nli_threshold.toFixed(2);
}

function formatNliScore(grounding: GroundingMetadata) {
  return grounding.min_entailment_score == null
    ? "未计算"
    : `${Math.round(grounding.min_entailment_score * 100)}%`;
}

function formatGroundingBlockedReason(reason: string | null | undefined) {
  if (reason === "unsupported_evidence_ref") {
    return "存在未提供的证据 ID";
  }
  if (reason === "structured_claims_parse_error") {
    return "模型草稿没有按结构化 claims JSON 输出";
  }
  if (reason === "empty_structured_claims") {
    return "结构化 claims 为空";
  }
  if (reason === "missing_tool_use") {
    return "模型未调用受控引用工具";
  }
  if (reason === "tool_name_mismatch") {
    return "模型调用了非预期工具";
  }
  if (reason === "tool_input_schema_error") {
    return "引用工具参数不符合结构化 schema";
  }
  if (reason === "empty_tool_claims") {
    return "引用工具 claims 为空";
  }
  if (reason === "claim_without_evidence_ref") {
    return "存在未声明证据 ID 的结构化 claim";
  }
  if (reason === "blank_claim_text") {
    return "存在内容为空的结构化 claim";
  }
  if (reason === "semantic_low_support") {
    return "存在与引用证据语义支持度过低的 claim";
  }
  if (reason === "nli_low_entailment") {
    return "存在未被引用证据蕴含的结构化 claim";
  }
  return "无";
}

function CitationListItem({ citation }: { citation: CitationCard }) {
  const isUploadedPdf = citation.source_type === "uploaded_pdf";
  const pdfPreviewUrl = isUploadedPdf && citation.pdf_upload_id ? buildPdfDownloadUrl(citation.pdf_upload_id) : null;
  return (
    <article style={getSurfaceCardStyle()}>
      <CardMetaRow
        items={[
          `来源 ${citation.source}`,
          `置信度 ${formatConfidence(citation.confidence)}`,
          isUploadedPdf ? "证据片段 来自上传 PDF" : null,
        ]}
      />
      <h3 style={{ color: "#1e293b", fontSize: 22, marginBottom: 12 }}>{citation.title}</h3>
      <CardBodyText>{citation.snippet}</CardBodyText>
      <EntityChips ids={citation.related_entity_ids ?? []} />
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
        <a href={`/literature/${encodeURIComponent(citation.literature_id)}`} style={{ color: "#0d9488", fontWeight: 700 }}>
          查看文献详情 →
        </a>
        {pdfPreviewUrl ? (
          <a href={pdfPreviewUrl} target="_blank" rel="noreferrer" style={{ color: "#0d9488", fontWeight: 700 }}>
            预览原文 PDF ↗
          </a>
        ) : null}
      </div>
    </article>
  );
}

export default function RagAnswerClient() {
  const searchParams = useSearchParams();
  const initialQuestion =
    searchParams.get("question")?.trim() || "特应性皮炎和肠-脑-皮肤轴有什么关系？";
  const [state, setState] = useState<RagState>({
    question: initialQuestion,
    source: "all",
    topK: 2,
    result: null,
    error: null,
    isLoading: false,
  });
  const statusCopy = getStatusCopy("rag", state.isLoading);
  const emptyStateCopy = getEmptyStateCopy("rag");
  const citationEmptyCopy = getCitationEmptyCopy();

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const question = String(form.get("question") ?? "").trim();
    const source = String(form.get("source") ?? "all") as RagSource;
    const rawTopK = Number(form.get("top_k") ?? state.topK);
    const topK = Number.isFinite(rawTopK) ? Math.max(1, Math.floor(rawTopK)) : 1;

    if (!question) {
      setState((current) => ({ ...current, question, source, topK, result: null, error: "请输入问题。" }));
      return;
    }

    setState((current) => ({ ...current, question, source, topK, result: null, error: null, isLoading: true }));

    try {
      const result = await answerRagQuestion(question, source, topK);
      setState({ question, source, topK, result, error: null, isLoading: false });
    } catch {
      setState({
        question,
        source,
        topK,
        result: null,
        error: emptyStateCopy.error,
        isLoading: false,
      });
    }
  }

  function onExportAnswer() {
    if (!state.result) {
      return;
    }
    const markdown = buildAnswerMarkdown(state.result);
    const fileName = buildAnswerMarkdownFileName(state.result.answered_at);
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = fileName;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
  }

  return (
    <div style={{ display: "grid", gap: 20 }}>
      <section style={getSurfaceSectionStyle()}>
        <div style={{ display: "grid", gap: 8, marginBottom: 20 }}>
          <h2 style={{ color: "#1e293b", fontSize: 24, margin: 0 }}>问答条件</h2>
          <p style={{ color: "#64748b", margin: 0, lineHeight: 1.6 }}>
            先明确问题，再限定来源与引用数量，随后核对回答、检索元数据与引用证据。
          </p>
        </div>

        <form onSubmit={onSubmit} style={{ display: "grid", gap: 16 }}>
          <label style={{ display: "grid", gap: 8, color: "#1e293b", fontWeight: 700 }}>
            问题
            <textarea
              name="question"
              value={state.question}
              onChange={(event) => setState((current) => ({ ...current, question: event.target.value }))}
              aria-label="RAG 问题"
              rows={4}
              style={{
                width: "100%",
                border: "1px solid #cbd5e1",
                borderRadius: 8,
                fontSize: 16,
                padding: "12px 14px",
                resize: "vertical",
              }}
            />
          </label>

          <div style={{ display: "flex", gap: 12, alignItems: "end", flexWrap: "wrap" }}>
            <label style={{ display: "grid", gap: 8, color: "#1e293b", fontWeight: 700 }}>
              文献来源
              <select
                name="source"
                value={state.source}
                onChange={(event) => setState((current) => ({ ...current, source: event.target.value as RagSource }))}
                aria-label="RAG 文献来源"
                style={{
                  minWidth: 180,
                  border: "1px solid #cbd5e1",
                  borderRadius: 8,
                  fontSize: 16,
                  padding: "12px 14px",
                }}
              >
                <option value="all">全部文献</option>
                <option value="cn_literature">中文文献</option>
                <option value="pubmed">PubMed</option>
              </select>
            </label>

            <label style={{ display: "grid", gap: 8, color: "#1e293b", fontWeight: 700 }}>
              引用数量 top_k
              <input
                name="top_k"
                type="number"
                min={1}
                value={state.topK}
                onChange={(event) => {
                  const nextValue = Number(event.target.value);
                  setState((current) => ({
                    ...current,
                    topK: Number.isFinite(nextValue) ? Math.max(1, Math.floor(nextValue)) : 1,
                  }));
                }}
                aria-label="引用数量"
                style={{
                  width: 140,
                  border: "1px solid #cbd5e1",
                  borderRadius: 8,
                  fontSize: 16,
                  padding: "12px 14px",
                }}
              />
            </label>

            <button
              type="submit"
              disabled={state.isLoading}
              style={{
                border: 0,
                borderRadius: 8,
                background: state.isLoading ? "#94a3b8" : "#0d9488",
                color: "white",
                fontSize: 16,
                fontWeight: 700,
                padding: "12px 20px",
                minHeight: 44,
              }}
            >
              {state.isLoading ? statusCopy.loadingLabel : statusCopy.submitLabel}
            </button>
          </div>
        </form>
      </section>

      {state.error ? <StatusPanel message={state.error} tone="error" /> : null}

      {state.result ? (
        <div style={{ display: "grid", gap: 20 }}>
          <section style={getSurfaceSectionStyle()}>
            <div style={{ display: "grid", gap: 4, marginBottom: 16 }}>
              <h2 style={{ color: "#1e293b", fontSize: 24, margin: 0 }}>回答结果</h2>
              <p style={{ color: "#64748b", margin: 0, lineHeight: 1.6 }}>
                先阅读结论，再回到下方引用卡片核对证据来源与检索边界。
              </p>
            </div>
            <CardMetaRow
              items={[
                `应用来源 ${getRagSourceLabel(state.result.retrieval.applied_source)}`,
                `应用 top_k ${state.result.retrieval.applied_top_k}`,
                `Provider ${state.result.provider_name}`,
                `检索策略 ${state.result.retrieval.strategy}`,
                `Grounding ${state.result.grounding.status}`,
                `Native Grounding ${formatNativeGrounding(state.result.grounding)}`,
                `句级引用覆盖 ${formatGroundingCoverage(state.result.grounding)}`,
                `结构化声明 ${formatStructuredClaimCount(state.result.grounding)}`,
              ]}
            />
            <h3 style={{ color: "#1e293b", fontSize: 28, marginTop: 12, marginBottom: 12 }}>{state.result.question}</h3>
            {state.result.grounding.status === "blocked" ? (
              <div style={{ marginBottom: 12 }}>
                <StatusPanel
                  message={`模型草稿未通过引用证据校验，已拦截展示。拦截原因：${formatGroundingBlockedReason(state.result.grounding.blocked_reason)}。`}
                  tone="warning"
                />
              </div>
            ) : null}
            <CardBodyText>{state.result.answer}</CardBodyText>
            <p style={{ color: "#64748b", marginBottom: 12, lineHeight: 1.6 }}>{state.result.disclaimer}</p>
            <button
              type="button"
              onClick={onExportAnswer}
              aria-label="导出答案为 Markdown"
              style={{
                border: "1px solid #0d9488",
                borderRadius: 8,
                background: "white",
                color: "#0d9488",
                fontSize: 15,
                fontWeight: 700,
                padding: "10px 18px",
                minHeight: 44,
                cursor: "pointer",
              }}
            >
              导出答案为 Markdown ↓
            </button>
          </section>

          <section style={getSurfaceSectionStyle()}>
            <div style={{ display: "grid", gap: 4, marginBottom: 12 }}>
              <h2 style={{ color: "#1e293b", fontSize: 24, margin: 0 }}>检索元数据</h2>
              <p style={{ color: "#64748b", margin: 0, lineHeight: 1.6 }}>用于确认当前回答实际使用的来源范围、引用上限与可核对证据数量。</p>
            </div>
            <CardMetaRow
              items={[
                `应用来源 ${getRagSourceLabel(state.result.retrieval.applied_source)}`,
                `应用 top_k ${state.result.retrieval.applied_top_k}`,
                `可用引用数 ${state.result.retrieval.available_citation_count}`,
                `Provider ${state.result.provider_name}`,
                `检索策略 ${state.result.retrieval.strategy}`,
                `Grounding ${state.result.grounding.status}`,
                `Grounding 策略 ${state.result.grounding.policy}`,
                `Native Grounding ${formatNativeGrounding(state.result.grounding)}`,
                `Grounding Tool ${formatGroundingTool(state.result.grounding)}`,
                `Tool 调用数 ${state.result.grounding.tool_call_count}`,
                `语义阈值 ${formatSemanticThreshold(state.result.grounding)}`,
                `最小语义支持度 ${formatSemanticScore(state.result.grounding)}`,
                `NLI 阈值 ${formatNliThreshold(state.result.grounding)}`,
                `最小蕴含支持度 ${formatNliScore(state.result.grounding)}`,
                `句级引用覆盖 ${formatGroundingCoverage(state.result.grounding)}`,
                `结构化声明 ${formatStructuredClaimCount(state.result.grounding)}`,
                `Token 输入 ${formatTokenUsage(state.result.input_tokens)}`,
                `Token 输出 ${formatTokenUsage(state.result.output_tokens)}`,
                `Provider 延迟 ${formatLatencyMs(state.result.sli)}`,
                `预估成本 ${formatEstimatedCost(state.result.sli)}`,
              ]}
            />
          </section>

          <section style={getSurfaceSectionStyle()}>
            <div style={{ display: "grid", gap: 4, marginBottom: 16 }}>
              <h2 style={{ color: "#1e293b", fontSize: 24, margin: 0 }}>引用卡片</h2>
              <p style={{ color: "#64748b", margin: 0, lineHeight: 1.6 }}>
                应用来源：{getRagSourceLabel(state.result.retrieval.applied_source)}；应用 top_k：
                {state.result.retrieval.applied_top_k}
              </p>
            </div>
            {state.result.citations.length > 0 ? (
              <div style={{ display: "grid", gap: 16 }}>
                {state.result.citations.map((citation) => (
                  <CitationListItem key={citation.literature_id} citation={citation} />
                ))}
              </div>
            ) : (
              <StatusPanel message={citationEmptyCopy} />
            )}
          </section>
        </div>
      ) : state.error ? null : (
        <StatusPanel message={emptyStateCopy.idle} />
      )}
    </div>
  );
}
