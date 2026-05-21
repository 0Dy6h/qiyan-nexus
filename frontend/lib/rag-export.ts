import type { CitationCard, RagAnswerResponse } from "./api/rag";
import { getRagSourceLabel } from "./api/rag";

const NEWLINE = "\n";

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
  sections.push("");
  sections.push("## 问题");
  sections.push("");
  sections.push(result.question);
  sections.push("");
  sections.push("## 回答");
  sections.push("");
  sections.push(result.answer);
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
