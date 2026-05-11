"use client";

import { FormEvent, useState } from "react";

import {
  getPdfParseStatusLabel,
  getLiteratureSourceLabel,
  LiteratureItem,
  LiteratureSearchSort,
  LiteratureSource,
  searchLiterature,
} from "../lib/api/literature";
import { getEmptyStateCopy, getStatusCopy } from "../lib/ui/states";
import { getSurfaceCardStyle, getSurfaceSectionStyle } from "../lib/ui/surfaces";
import { CardBodyText, CardMetaRow } from "./CardMeta";
import StatusPanel from "./StatusPanel";

type SearchState = {
  query: string;
  source: LiteratureSource;
  sort: LiteratureSearchSort;
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  items: LiteratureItem[];
  error: string | null;
  isLoading: boolean;
  hasSearched: boolean;
};

export default function LiteratureSearchClient() {
  const [state, setState] = useState<SearchState>({
    query: "特应性皮炎",
    source: "all",
    sort: "relevance",
    page: 1,
    pageSize: 10,
    total: 0,
    totalPages: 0,
    items: [],
    error: null,
    isLoading: false,
    hasSearched: false,
  });
  const statusCopy = getStatusCopy("literature", state.isLoading);
  const emptyStateCopy = getEmptyStateCopy("literature");

  async function runSearch(
    query: string,
    source: LiteratureSource,
    page: number,
    pageSize: number,
    sort: LiteratureSearchSort,
  ) {
    setState((current) => ({
      ...current,
      query,
      source,
      sort,
      page,
      pageSize,
      items: [],
      error: null,
      isLoading: true,
      hasSearched: true,
    }));

    try {
      const result = await searchLiterature(query, source, page, pageSize, sort);
      setState({
        query: result.query,
        source: result.source,
        sort: result.sort,
        page: result.page,
        pageSize: result.page_size,
        total: result.total,
        totalPages: result.total_pages,
        items: result.items,
        error: null,
        isLoading: false,
        hasSearched: true,
      });
    } catch {
      setState({
        query,
        source,
        sort,
        page,
        pageSize,
        total: 0,
        totalPages: 0,
        items: [],
        error: emptyStateCopy.error,
        isLoading: false,
        hasSearched: true,
      });
    }
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const query = String(form.get("q") ?? "").trim();
    const source = String(form.get("source") ?? "all") as LiteratureSource;
    const sort = String(form.get("sort") ?? "relevance") as LiteratureSearchSort;
    const pageSize = Number(form.get("page_size") ?? state.pageSize);

    if (!query) {
      setState((current) => ({
        ...current,
        query,
        source,
        sort,
        items: [],
        error: "请输入检索关键词。",
        hasSearched: true,
      }));
      return;
    }

    await runSearch(query, source, 1, pageSize, sort);
  }

  return (
    <div style={{ display: "grid", gap: 20 }}>
      <section style={getSurfaceSectionStyle()}>
        <div style={{ display: "grid", gap: 8, marginBottom: 20 }}>
          <h2 style={{ color: "#1e293b", fontSize: 24, margin: 0 }}>检索条件</h2>
          <p style={{ color: "#64748b", margin: 0, lineHeight: 1.6 }}>
            先限定关键词、来源与排序方式，再进入结果核对与原文追踪。
          </p>
        </div>

        <form onSubmit={onSubmit} style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
          <input
            name="q"
            defaultValue={state.query}
            aria-label="检索关键词"
            style={{
              flex: 1,
              border: "1px solid #cbd5e1",
              borderRadius: 8,
              fontSize: 16,
              minWidth: 220,
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
          <select
            name="sort"
            defaultValue={state.sort}
            aria-label="排序方式"
            style={{
              border: "1px solid #cbd5e1",
              borderRadius: 8,
              fontSize: 16,
              padding: "12px 14px",
            }}
          >
            <option value="relevance">相关度</option>
            <option value="year_desc">年份降序</option>
            <option value="year_asc">年份升序</option>
          </select>
          <select
            name="page_size"
            defaultValue={state.pageSize}
            aria-label="每页数量"
            style={{
              border: "1px solid #cbd5e1",
              borderRadius: 8,
              fontSize: 16,
              padding: "12px 14px",
            }}
          >
            <option value="5">5 条/页</option>
            <option value="10">10 条/页</option>
            <option value="20">20 条/页</option>
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
              minHeight: 44,
            }}
          >
            {state.isLoading ? statusCopy.loadingLabel : statusCopy.submitLabel}
          </button>
        </form>
      </section>

      {state.error ? <StatusPanel message={state.error} tone="error" /> : null}

      {!state.error && state.total > 0 ? (
        <section style={getSurfaceSectionStyle()}>
          <div
            style={{
              alignItems: "center",
              color: "#475569",
              display: "flex",
              flexWrap: "wrap",
              fontSize: 14,
              gap: 12,
              justifyContent: "space-between",
              marginBottom: 16,
            }}
          >
            <div style={{ display: "grid", gap: 4 }}>
              <h2 style={{ color: "#1e293b", fontSize: 24, margin: 0 }}>检索结果</h2>
              <span>
                共 {state.total} 条结果，第 {state.page} / {state.totalPages} 页
              </span>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                type="button"
                disabled={state.isLoading || state.page <= 1}
                onClick={() => runSearch(state.query, state.source, state.page - 1, state.pageSize, state.sort)}
                style={{
                  border: "1px solid #cbd5e1",
                  borderRadius: 8,
                  background: "white",
                  color: "#0f172a",
                  padding: "8px 12px",
                  minHeight: 40,
                }}
              >
                上一页
              </button>
              <button
                type="button"
                disabled={state.isLoading || state.page >= state.totalPages}
                onClick={() => runSearch(state.query, state.source, state.page + 1, state.pageSize, state.sort)}
                style={{
                  border: "1px solid #cbd5e1",
                  borderRadius: 8,
                  background: "white",
                  color: "#0f172a",
                  padding: "8px 12px",
                  minHeight: 40,
                }}
              >
                下一页
              </button>
            </div>
          </div>

          <div style={{ display: "grid", gap: 16 }}>
            {state.items.map((item) => (
              <article key={item.id} style={getSurfaceCardStyle()}>
                <CardMetaRow
                  items={[
                    item.language === "zh" ? "中文" : "英文",
                    getLiteratureSourceLabel(item.source_type),
                    item.source,
                    String(item.year),
                    getPdfParseStatusLabel(item.pdf_parse_status ?? null),
                  ]}
                />
                <h3 style={{ color: "#1e293b", fontSize: 22, marginBottom: 12 }}>{item.title}</h3>
                <CardBodyText>{item.snippet}</CardBodyText>
                <a href={`/literature/${encodeURIComponent(item.id)}`} style={{ color: "#0d9488", fontWeight: 700 }}>
                  查看详情 →
                </a>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      {state.items.length > 0 || state.isLoading || state.error ? null : (
        <StatusPanel message={state.hasSearched ? "未检索到匹配文献，请调整关键词或来源。" : emptyStateCopy.idle} />
      )}
    </div>
  );
}
