"use client";

import { FormEvent, useState } from "react";

import {
  getLiteratureSourceLabel,
  LiteratureItem,
  LiteratureSource,
  searchLiterature,
} from "../lib/api/literature";
import { getEmptyStateCopy, getStatusCopy } from "../lib/ui/states";
import { CardBodyText, CardMetaRow } from "./CardMeta";
import StatusPanel from "./StatusPanel";

type SearchState = {
  query: string;
  source: LiteratureSource;
  items: LiteratureItem[];
  error: string | null;
  isLoading: boolean;
};

export default function LiteratureSearchClient() {
  const [state, setState] = useState<SearchState>({
    query: "特应性皮炎",
    source: "all",
    items: [],
    error: null,
    isLoading: false,
  });
  const statusCopy = getStatusCopy("literature", state.isLoading);
  const emptyStateCopy = getEmptyStateCopy("literature");

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const query = String(form.get("q") ?? "").trim();
    const source = String(form.get("source") ?? "all") as LiteratureSource;

    if (!query) {
      setState((current) => ({ ...current, query, source, items: [], error: "请输入检索关键词。" }));
      return;
    }

    setState((current) => ({ ...current, query, source, items: [], error: null, isLoading: true }));

    try {
      const result = await searchLiterature(query, source);
      setState({ query: result.query, source, items: result.items, error: null, isLoading: false });
    } catch {
      setState({ query, source, items: [], error: emptyStateCopy.error, isLoading: false });
    }
  }

  return (
    <>
      <form onSubmit={onSubmit} style={{ display: "flex", gap: 12, margin: "32px 0" }}>
        <input
          name="q"
          defaultValue={state.query}
          aria-label="检索关键词"
          style={{
            flex: 1,
            border: "1px solid #cbd5e1",
            borderRadius: 8,
            fontSize: 16,
            padding: "12px 14px",
          }}
        />
        <select
          name="source"
          defaultValue={state.source}
          aria-label="文献来源"
          style={{
            border: "1px solid #cbd5e1",
            borderRadius: 8,
            fontSize: 16,
            padding: "12px 14px",
          }}
        >
          <option value="all">全部</option>
          <option value="cn_literature">中文文献</option>
          <option value="pubmed">PubMed</option>
        </select>
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
      </form>

      {state.error ? <StatusPanel message={state.error} tone="error" /> : null}

      {state.items.length > 0 ? (
        <div style={{ display: "grid", gap: 16 }}>
          {state.items.map((item) => (
            <article
              key={item.id}
              style={{
                background: "white",
                border: "1px solid #e2e8f0",
                borderRadius: 12,
                padding: 24,
              }}
            >
              <CardMetaRow
                items={[
                  item.language === "zh" ? "中文" : "英文",
                  getLiteratureSourceLabel(item.source_type),
                  item.source,
                  String(item.year),
                ]}
              />
              <h2 style={{ color: "#1e293b", fontSize: 22 }}>{item.title}</h2>
              <CardBodyText>{item.snippet}</CardBodyText>
              <a href={`/literature/${encodeURIComponent(item.id)}`} style={{ color: "#0d9488", fontWeight: 700 }}>
                查看详情 →
              </a>
            </article>
          ))}
        </div>
      ) : state.isLoading || state.error ? null : (
        <StatusPanel message={emptyStateCopy.idle} />
      )}
    </>
  );
}
