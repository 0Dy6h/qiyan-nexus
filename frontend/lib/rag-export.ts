import type { CitationCard, ProviderSli, RagAnswerResponse } from "./api/rag";
import { getRagSourceLabel } from "./api/rag";

const NEWLINE = "\n";

function joinOrFallback(items: string[], fallback: string): string {
  return items.length > 0 ? items.join("、") : fallback;
}

function formatLatencyMs(sli: ProviderSli | null | undefined): string {
  return sli?.provider_latency_ms == null ? "未返回" : `${sli.provider_latency_ms} ms`;
}

function formatEstimatedCost(sli: ProviderSli | null | undefined): string {
  return sli?.estimated_cost_usd == null ? "未估算" : `$${sli.estimated_cost_usd.toFixed(6)}`;
}

function formatSemanticThreshold(threshold: number | null | undefined): string {
  return threshold == null ? "未启用" : threshold.toFixed(2);
}

function formatSemanticScore(score: number | null | undefined): string {
  return score == null ? "未计算" : `${Math.round(score * 100)}%`;
}

function formatCitationBlock(citation: CitationCard, index: number): string {
  const lines: string[] = [];
  lines.push(`### 引用 ${index + 1} — ${citation.title}`);
  const meta: string[] = [
    `来源：${citation.source}`,
    `literature_id：${citation.literature_id}`,
    `置信度：${Math.round(citation.confidence * 100)}%`,
  ];
  if (citation.chunk_id) {
    meta.push(`chunk_id：${citation.chunk_id}`);
  }
  if (citation.source_type) {
    meta.push(`source_type：${citation.source_type}`);
  }
  if (citation.pdf_upload_id) {
    meta.push(`pdf_upload_id：${citation.pdf_upload_id}`);
  }
  lines.push(meta.join(" · "));
  lines.push("");
  lines.push(`> ${citation.snippet}`);
  if (citation.quote) {
    lines.push("");
    lines.push(`证据片段引文：${citation.quote}`);
  }
  if (citation.reason) {
    lines.push("");
    lines.push(`命中证据标签：${citation.reason}`);
  }
  return lines.join(NEWLINE);
}

export function buildAnswerMarkdown(result: RagAnswerResponse): string {
  const sections: string[] = [];
  sections.push("# Qiyan Nexus RAG 答案导出");
  sections.push("");
  sections.push(`- 导出时间（UTC）：${result.answered_at}`);
  sections.push(`- 应用来源：${getRagSourceLabel(result.retrieval.applied_source)}`);
  sections.push(`- 应用 top_k：${result.retrieval.applied_top_k}`);
  sections.push(`- 可用引用数：${result.retrieval.available_citation_count}`);
  sections.push(`- Provider：${result.provider_name}`);
  sections.push(`- 检索策略：${result.retrieval.strategy}`);
  sections.push(`- Grounding 状态：${result.grounding.status}`);
  sections.push(`- Grounding 策略：${result.grounding.policy}`);
  sections.push(`- Provider-native grounding：${result.grounding.provider_native_grounding}`);
  sections.push(`- Grounding Tool：${result.grounding.tool_name ?? "无"}`);
  sections.push(`- Tool 调用数：${result.grounding.tool_call_count}`);
  sections.push(`- 语义阈值：${formatSemanticThreshold(result.grounding.semantic_threshold)}`);
  sections.push(`- 最小语义支持度：${formatSemanticScore(result.grounding.min_semantic_score)}`);
  sections.push(`- Grounding 拦截原因：${result.grounding.blocked_reason ?? "无"}`);
  sections.push(`- 句级引用覆盖：${result.grounding.cited_claim_count}/${result.grounding.claim_count}`);
  sections.push(
    `- Grounding 命中证据：${joinOrFallback(result.grounding.matched_evidence_refs, "无")}`,
  );
  sections.push(
    `- Grounding 异常证据：${joinOrFallback(result.grounding.unsupported_evidence_refs, "无")}`,
  );
  sections.push(`- 结构化声明数：${result.grounding.structured_claims.length}`);
  sections.push(`- Token 输入：${result.input_tokens ?? "未返回"}`);
  sections.push(`- Token 输出：${result.output_tokens ?? "未返回"}`);
  sections.push(`- Provider 延迟：${formatLatencyMs(result.sli)}`);
  sections.push(`- 预估成本：${formatEstimatedCost(result.sli)}`);
  sections.push("");
  sections.push("## 问题");
  sections.push("");
  sections.push(result.question);
  sections.push("");
  sections.push("## 回答");
  sections.push("");
  sections.push(result.answer);
  sections.push("");
  sections.push("## 结构化声明");
  sections.push("");
  if (result.grounding.structured_claims.length === 0) {
    sections.push("（当前回答没有结构化声明。）");
  } else {
    result.grounding.structured_claims.forEach((claim, index) => {
      sections.push(`### Claim ${index + 1}`);
      sections.push("");
      sections.push(claim.text);
      sections.push("");
      sections.push(`evidence_refs：${joinOrFallback(claim.evidence_refs, "无")}`);
      sections.push("");
    });
  }
  sections.push("");
  sections.push("## 引用证据");
  sections.push("");
  if (result.citations.length === 0) {
    sections.push("（当前回答没有可核对的引用证据。）");
  } else {
    result.citations.forEach((citation, index) => {
      sections.push(formatCitationBlock(citation, index));
      sections.push("");
    });
  }
  sections.push("---");
  sections.push("");
  sections.push(result.disclaimer);
  sections.push("");
  return sections.join(NEWLINE);
}

export function buildAnswerMarkdownFileName(answeredAt: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(answeredAt);
  if (!match) {
    return "qiyan-rag-answer.md";
  }
  const [, y, mo, d, h, mi] = match;
  return `qiyan-rag-answer-${y}${mo}${d}-${h}${mi}.md`;
}
