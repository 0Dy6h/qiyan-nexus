"use client";

import { FormEvent, useState } from "react";

import { LiteratureItem, searchLiterature } from "../lib/api/literature";

type SearchState = {
  query: string;
  items: LiteratureItem[];
  error: string | null;
  isLoading: boolean;
};

export default function LiteratureSearchClient() {
  const [state, setState] = useState<SearchState>({
    query: "特应性皮炎",
    items: [],
    error: null,
    isLoading: false,
  });

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const query = String(form.get("q") ?? "").trim();

    if (!query) {
      setState((current) => ({ ...current, query, items: [], error: "请输入检索关键词。" }));
      return;
    }

    setState((current) => ({ ...current, query, error: null, isLoading: true }));

    try {
      const result = await searchLiterature(query);
      setState({ query: result.query, items: result.items, error: null, isLoading: false });
    } catch {
      setState({ query, items: [], error: "文献检索失败，请确认后端服务已启动。", isLoading: false });
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
          {state.isLoading ? "搜索中" : "搜索"}
        </button>
      </form>

      {state.error ? <p style={{ color: "#b45309" }}>{state.error}</p> : null}

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
              <p style={{ color: "#64748b", margin: 0 }}>
                {item.language === "zh" ? "中文" : "英文"} · {item.source_type === "pubmed" ? "PubMed" : "中文文献"} · {item.source} · {item.year}
              </p>
              <h2 style={{ color: "#1e293b", fontSize: 22 }}>{item.title}</h2>
              <p style={{ color: "#475569" }}>{item.snippet}</p>
            </article>
          ))}
        </div>
      ) : (
        <p style={{ color: "#64748b" }}>输入关键词后，从后端 API 获取文献结果。</p>
      )}
    </>
  );
}
