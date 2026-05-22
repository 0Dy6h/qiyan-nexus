"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

import {
  fetchNetworkResult,
  getNetworkAnalysisTypeLabel,
  NetworkAnalysisResult,
  NetworkAnalysisType,
  submitNetworkAnalysis,
} from "../lib/api/network";
import { getSurfaceCardStyle, getSurfaceSectionStyle } from "../lib/ui/surfaces";
import StatusPanel from "./StatusPanel";

type NetworkPhase = "idle" | "submitting" | "polling" | "completed" | "error";

const POLL_INTERVAL_MS = 800;
const MAX_POLL_ATTEMPTS = 10;

function formatScore(value: number) {
  return `${Math.round(value * 100)}%`;
}

export default function NetworkAnalysisClient() {
  const [query, setQuery] = useState("消风散");
  const [analysisType, setAnalysisType] = useState<NetworkAnalysisType>("formula");
  const [phase, setPhase] = useState<NetworkPhase>("idle");
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<NetworkAnalysisResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  async function pollUntilCompleted(taskId: string) {
    for (let attempt = 0; attempt < MAX_POLL_ATTEMPTS; attempt += 1) {
      if (!mountedRef.current) {
        return;
      }
      try {
        const polled = await fetchNetworkResult(taskId);
        if (!mountedRef.current) {
          return;
        }
        setProgress(polled.progress);
        if (polled.status === "completed" && polled.result) {
          setResult(polled.result);
          setPhase("completed");
          return;
        }
      } catch {
        if (!mountedRef.current) {
          return;
        }
        setErrorMessage("轮询任务结果失败，请确认后端服务已启动。");
        setPhase("error");
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
    }
    if (mountedRef.current) {
      setErrorMessage("任务在限定轮询次数内未完成，请稍后重试。");
      setPhase("error");
    }
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      setErrorMessage("请输入复方或单味中药名称。");
      setPhase("error");
      return;
    }

    setErrorMessage(null);
    setResult(null);
    setProgress(0);
    setPhase("submitting");

    try {
      const accepted = await submitNetworkAnalysis(trimmedQuery, analysisType);
      if (!mountedRef.current) {
        return;
      }
      setProgress(accepted.progress);
      setPhase("polling");
      await pollUntilCompleted(accepted.task_id);
    } catch {
      if (!mountedRef.current) {
        return;
      }
      setErrorMessage("提交分析任务失败，请确认后端服务已启动。");
      setPhase("error");
    }
  }

  const isBusy = phase === "submitting" || phase === "polling";
  const submitLabel = isBusy
    ? phase === "submitting"
      ? "提交中..."
      : `运行中... ${progress}%`
    : "开始分析";

  return (
    <div style={{ display: "grid", gap: 20 }}>
      <section style={getSurfaceSectionStyle()}>
        <div style={{ display: "grid", gap: 8, marginBottom: 20 }}>
          <h2 style={{ color: "#1e293b", fontSize: 24, margin: 0 }}>分析条件</h2>
          <p style={{ color: "#64748b", margin: 0, lineHeight: 1.6 }}>
            输入复方或单味中药名称，后端会按 mock 数据返回「成分-靶点-通路-疾病」链，仅用于流程演示。
          </p>
        </div>

        <form onSubmit={onSubmit} style={{ display: "grid", gap: 16 }}>
          <label style={{ display: "grid", gap: 8, color: "#1e293b", fontWeight: 700 }}>
            分析对象
            <input
              name="query"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              aria-label="网络药理学分析对象"
              style={{
                width: "100%",
                border: "1px solid #cbd5e1",
                borderRadius: 8,
                fontSize: 16,
                padding: "12px 14px",
              }}
            />
          </label>

          <div style={{ display: "flex", gap: 12, alignItems: "end", flexWrap: "wrap" }}>
            <label style={{ display: "grid", gap: 8, color: "#1e293b", fontWeight: 700 }}>
              对象类型
              <select
                name="analysis_type"
                value={analysisType}
                onChange={(event) => setAnalysisType(event.target.value as NetworkAnalysisType)}
                aria-label="网络药理学对象类型"
                style={{
                  minWidth: 180,
                  border: "1px solid #cbd5e1",
                  borderRadius: 8,
                  fontSize: 16,
                  padding: "12px 14px",
                }}
              >
                <option value="formula">复方</option>
                <option value="herb">单味中药</option>
              </select>
            </label>

            <button
              type="submit"
              disabled={isBusy}
              style={{
                border: 0,
                borderRadius: 8,
                background: isBusy ? "#94a3b8" : "#0d9488",
                color: "white",
                fontSize: 16,
                fontWeight: 700,
                padding: "12px 20px",
                minHeight: 44,
              }}
            >
              {submitLabel}
            </button>
          </div>
        </form>
      </section>

      {phase === "error" && errorMessage ? <StatusPanel message={errorMessage} tone="error" /> : null}

      {phase === "completed" && result ? (
        <section style={getSurfaceSectionStyle()}>
          <div style={{ display: "grid", gap: 4, marginBottom: 16 }}>
            <h2 style={{ color: "#1e293b", fontSize: 24, margin: 0 }}>「成分-靶点-通路-疾病」链</h2>
            <p style={{ color: "#64748b", margin: 0, lineHeight: 1.6 }}>
              分析对象 {result.query}（{getNetworkAnalysisTypeLabel(result.analysis_type)}）共返回 {result.chains.length} 条链；分数为
              mock 置信度，仅用于 UI 演示。
            </p>
          </div>
          <div style={{ display: "grid", gap: 12 }}>
            {result.chains.map((chain, index) => (
              <article key={`${chain.compound}-${index}`} style={getSurfaceCardStyle()}>
                <p style={{ color: "#0d9488", fontWeight: 700, margin: 0, fontSize: 13 }}>
                  链 #{index + 1} · 置信度 {formatScore(chain.score)}
                </p>
                <p style={{ color: "#1e293b", fontSize: 18, margin: "8px 0 0", lineHeight: 1.6 }}>
                  {chain.herb} → {chain.compound} → {chain.target} → {chain.pathway} → {chain.disease}
                </p>
              </article>
            ))}
          </div>
          <p style={{ color: "#64748b", marginTop: 16, marginBottom: 0, lineHeight: 1.6 }}>
            {result.disclaimer}
          </p>
        </section>
      ) : phase === "idle" ? (
        <StatusPanel message="提交分析任务后，从后端 /api/network/analyze 获取 mock 链。" />
      ) : isBusy ? (
        <StatusPanel message={`分析任务运行中... 当前进度 ${progress}%。`} />
      ) : null}
    </div>
  );
}
