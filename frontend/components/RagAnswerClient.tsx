"use client";

import { FormEvent, useState } from "react";

import {
  answerRagQuestion,
  CitationCard,
  getRagSourceLabel,
  RagAnswerResponse,
  RagSource,
} from "../lib/api/rag";
import { getEmptyStateCopy, getStatusCopy } from "../lib/ui/states";
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
    <article
      style={{
        background: "white",
        border: "1px solid #e2e8f0",
        borderRadius: 12,
        padding: 20,
      }}
    >
      <CardMetaRow items={["证据来源", citation.source, `置信度 ${formatConfidence(citation.confidence)}`]} />
      <h3 style={{ color: "#1e293b", fontSize: 20 }}>{citation.title}</h3>
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
    <>
      <form onSubmit={onSubmit} style={{ display: "grid", gap: 16, margin: "32px 0" }}>
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
            }}
          >
            {state.isLoading ? statusCopy.loadingLabel : statusCopy.submitLabel}
          </button>
        </div>
      </form>

      {state.error ? <StatusPanel message={state.error} tone="error" /> : null}

      {state.result ? (
        <div style={{ display: "grid", gap: 20 }}>
          <section
            style={{
              background: "white",
              border: "1px solid #e2e8f0",
              borderRadius: 12,
              padding: 24,
            }}
          >
            <p style={{ color: "#64748b", marginTop: 0 }}>当前问题</p>
            <h2 style={{ color: "#1e293b", fontSize: 28 }}>{state.result.question}</h2>
            <p style={{ color: "#334155", fontSize: 17, lineHeight: 1.7 }}>{state.result.answer}</p>
            <p style={{ color: "#64748b", marginBottom: 0 }}>{state.result.disclaimer}</p>
          </section>

          <section
            style={{
              background: "#ecfeff",
              border: "1px solid #99f6e4",
              borderRadius: 12,
              padding: 20,
            }}
          >
            <h3 style={{ color: "#115e59", marginTop: 0 }}>检索元数据</h3>
            <ul style={{ color: "#134e4a", margin: 0, paddingLeft: 20 }}>
              <li>应用来源：{getRagSourceLabel(state.result.retrieval.applied_source)}</li>
              <li>应用 top_k：{state.result.retrieval.applied_top_k}</li>
              <li>当前可用引用数：{state.result.retrieval.available_citation_count}</li>
            </ul>
          </section>

          <section style={{ display: "grid", gap: 16 }}>
            <div>
              <h3 style={{ color: "#1e293b", marginBottom: 8 }}>引用卡片</h3>
              <p style={{ color: "#64748b", marginTop: 0 }}>
                当前来源过滤：{getRagSourceLabel(state.source)}；请求 top_k：{state.topK}
              </p>
            </div>
            {state.result.citations.map((citation) => (
              <CitationListItem key={citation.literature_id} citation={citation} />
            ))}
          </section>
        </div>
      ) : state.error ? null : (
        <StatusPanel message={emptyStateCopy.idle} />
      )}
    </>
  );
}
