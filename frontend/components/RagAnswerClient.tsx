"use client";

import { FormEvent, useState } from "react";

import {
  answerRagQuestion,
  CitationCard,
  getRagSourceLabel,
  RagAnswerResponse,
  RagSource,
} from "../lib/api/rag";
import { getCitationEmptyCopy, getEmptyStateCopy, getStatusCopy } from "../lib/ui/states";
import { getSurfaceCardStyle, getSurfaceSectionStyle } from "../lib/ui/surfaces";
import { CardBodyText, CardMetaRow } from "./CardMeta";
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

function CitationListItem({ citation }: { citation: CitationCard }) {
  return (
    <article style={getSurfaceCardStyle()}>
      <CardMetaRow items={["证据来源", citation.source, `置信度 ${formatConfidence(citation.confidence)}`]} />
      <h3 style={{ color: "#1e293b", fontSize: 22, marginBottom: 12 }}>{citation.title}</h3>
      <CardBodyText>{citation.snippet}</CardBodyText>
      <a href={`/literature/${encodeURIComponent(citation.literature_id)}`} style={{ color: "#0d9488", fontWeight: 700 }}>
        查看文献详情 →
      </a>
    </article>
  );
}

export default function RagAnswerClient() {
  const [state, setState] = useState<RagState>({
    question: "特应性皮炎和肠-脑-皮肤轴有什么关系？",
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
            <CardMetaRow items={[`当前来源 ${getRagSourceLabel(state.result.retrieval.applied_source)}`, `当前 top_k ${state.result.retrieval.applied_top_k}`]} />
            <h3 style={{ color: "#1e293b", fontSize: 28, marginTop: 12, marginBottom: 12 }}>{state.result.question}</h3>
            <CardBodyText>{state.result.answer}</CardBodyText>
            <p style={{ color: "#64748b", marginBottom: 0, lineHeight: 1.6 }}>{state.result.disclaimer}</p>
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
                `当前可用引用数 ${state.result.retrieval.available_citation_count}`,
              ]}
            />
          </section>

          <section style={getSurfaceSectionStyle()}>
            <div style={{ display: "grid", gap: 4, marginBottom: 16 }}>
              <h2 style={{ color: "#1e293b", fontSize: 24, margin: 0 }}>引用卡片</h2>
              <p style={{ color: "#64748b", margin: 0, lineHeight: 1.6 }}>
                当前来源过滤：{getRagSourceLabel(state.source)}；请求 top_k：{state.topK}
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
