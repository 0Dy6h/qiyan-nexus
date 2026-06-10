"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  getLiteratureDataSourceFilter,
  getPdfParseStatusLabel,
  getLiteratureSourceLabel,
  LiteratureDataSourceView,
  LiteratureItem,
  LiteratureSearchSort,
  searchLiterature,
} from "../lib/api/literature";
import { getEmptyStateCopy, getStatusCopy } from "../lib/ui/states";
import LiteratureDataSourceBanner from "./LiteratureDataSourceBanner";
import StatusPanel from "./StatusPanel";

type SearchState = {
  query: string;
  view: LiteratureDataSourceView;
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
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q")?.trim() || "特应性皮炎";
  const appliedQueryRef = useRef<string | null>(null);
  const [state, setState] = useState<SearchState>({
    query: initialQuery,
    view: "all",
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
    view: LiteratureDataSourceView,
    page: number,
    pageSize: number,
    sort: LiteratureSearchSort,
  ) {
    setState((current) => ({
      ...current,
      query,
      view,
      sort,
      page,
      pageSize,
      items: [],
      error: null,
      isLoading: true,
      hasSearched: true,
    }));

    const filter = getLiteratureDataSourceFilter(view);
    try {
      const result = await searchLiterature(
        query,
        filter.source,
        page,
        pageSize,
        sort,
        filter.hasPdfUpload,
      );
      setState({
        query: result.query,
        view,
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
        view,
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
    const view = String(form.get("view") ?? "all") as LiteratureDataSourceView;
    const sort = String(form.get("sort") ?? "relevance") as LiteratureSearchSort;
    const pageSize = Number(form.get("page_size") ?? state.pageSize);

    if (!query) {
      setState((current) => ({
        ...current,
        query,
        view,
        sort,
        items: [],
        error: "请输入检索关键词。",
        hasSearched: true,
      }));
      return;
    }

    await runSearch(query, view, 1, pageSize, sort);
  }

  useEffect(() => {
    const linkedQuery = searchParams.get("q")?.trim();
    if (!linkedQuery || appliedQueryRef.current === linkedQuery) {
      return;
    }
    appliedQueryRef.current = linkedQuery;
    void runSearch(linkedQuery, "all", 1, state.pageSize, "relevance");
    // runSearch intentionally stays out of the dependency list so a linked query
    // triggers one search rather than resubmitting on every state update.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, state.pageSize]);

  return (
    <div className="grid gap-5">
      <LiteratureDataSourceBanner view={state.view} />

      <Card>
        <CardHeader>
          <CardTitle>检索条件</CardTitle>
          <p className="text-gray-600 text-sm leading-relaxed">
            先明确关键词，再限定来源、排序与每页数量，随后进入结果核对与原文追踪。
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="grid gap-4">
            <div className="grid gap-2">
              <label htmlFor="search-query" className="text-gray-900 font-semibold text-sm">
                检索关键词
              </label>
              <Input
                id="search-query"
                name="q"
                value={state.query}
                onChange={(event) => setState((current) => ({ ...current, query: event.target.value }))}
                className="border-gray-300 focus-visible:ring-primary-500"
              />
            </div>

            <div className="flex gap-3 items-end flex-wrap">
              <div className="grid gap-2">
                <label htmlFor="view" className="text-gray-900 font-semibold text-sm">
                  文献来源
                </label>
                <select
                  id="view"
                  name="view"
                  defaultValue={state.view}
                  className="h-10 rounded-md border border-gray-300 bg-white px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
                >
                  <option value="all">全部来源</option>
                  <option value="pubmed_live">PubMed 实时</option>
                  <option value="cnki_sample">CNKI sample</option>
                  <option value="uploaded_pdf">上传 PDF</option>
                </select>
              </div>

              <div className="grid gap-2">
                <label htmlFor="sort" className="text-gray-900 font-semibold text-sm">
                  排序方式
                </label>
                <select
                  id="sort"
                  name="sort"
                  defaultValue={state.sort}
                  className="h-10 rounded-md border border-gray-300 bg-white px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
                >
                  <option value="relevance">相关度</option>
                  <option value="year_desc">年份降序</option>
                  <option value="year_asc">年份升序</option>
                </select>
              </div>

              <div className="grid gap-2">
                <label htmlFor="page_size" className="text-gray-900 font-semibold text-sm">
                  每页数量
                </label>
                <select
                  id="page_size"
                  name="page_size"
                  defaultValue={state.pageSize}
                  className="h-10 rounded-md border border-gray-300 bg-white px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
                >
                  <option value="5">5 条/页</option>
                  <option value="10">10 条/页</option>
                  <option value="20">20 条/页</option>
                </select>
              </div>

              <Button type="submit" disabled={state.isLoading} className="bg-primary-600 hover:bg-primary-700">
                {state.isLoading ? statusCopy.loadingLabel : statusCopy.submitLabel}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {state.error ? <StatusPanel message={state.error} tone="error" /> : null}

      {!state.error && state.total > 0 ? (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div className="grid gap-1">
                <CardTitle>检索结果</CardTitle>
                <p className="text-gray-600 text-sm">
                  共 {state.total} 条结果，第 {state.page} / {state.totalPages} 页；请优先核对来源、年份与解析状态。
                </p>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={state.isLoading || state.page <= 1}
                  onClick={() => runSearch(state.query, state.view, state.page - 1, state.pageSize, state.sort)}
                >
                  上一页
                </Button>
                <Button
                  size="sm"
                  disabled={state.isLoading || state.page >= state.totalPages}
                  onClick={() => runSearch(state.query, state.view, state.page + 1, state.pageSize, state.sort)}
                  className="bg-primary-600 hover:bg-primary-700"
                >
                  下一页
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4">
              {state.items.map((item) => (
                <Card key={item.id} className="hover:shadow-md transition-shadow">
                  <CardContent className="pt-6">
                    <div className="flex gap-2 flex-wrap mb-3">
                      <Badge variant="secondary" className="text-xs">
                        语言 {item.language === "zh" ? "中文" : "英文"}
                      </Badge>
                      <Badge variant="outline" className="text-xs">
                        来源 {getLiteratureSourceLabel(item.source_type)}
                      </Badge>
                      <Badge variant="outline" className="text-xs">
                        期刊 {item.source}
                      </Badge>
                      <Badge variant="outline" className="text-xs">
                        年份 {String(item.year)}
                      </Badge>
                      <Badge variant="outline" className="text-xs">
                        解析状态 {getPdfParseStatusLabel(item.pdf_parse_status ?? null)}
                      </Badge>
                    </div>
                    <h3 className="text-gray-900 text-xl font-semibold mb-3">{item.title}</h3>
                    <p className="text-gray-600 text-sm leading-relaxed mb-3">{item.snippet}</p>
                    <a href={`/literature/${encodeURIComponent(item.id)}`} className="text-primary-600 font-semibold hover:underline text-sm">
                      查看详情 →
                    </a>
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>
      ) : null}

      {state.items.length > 0 || state.isLoading || state.error ? null : (
        <StatusPanel message={state.hasSearched ? "未检索到匹配文献，请调整关键词、来源或排序后重试。" : emptyStateCopy.idle} />
      )}
    </div>
  );
}
