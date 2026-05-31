import type { NetworkAnalysisResult, NetworkChain } from "./api/network";
import { getNetworkAnalysisTypeLabel } from "./api/network";

const NEWLINE = "\n";

function escapeTableCell(value: string | number | null | undefined): string {
  const text = value === null || value === undefined || value === "" ? "无" : String(value);
  return text.replaceAll("|", "\\|").replace(/\s+/g, " ").trim();
}

function formatScore(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function formatEntityIds(ids: string[]): string {
  return ids.length > 0 ? ids.join(", ") : "无";
}

function formatChainRow(chain: NetworkChain, index: number): string {
  return [
    index + 1,
    chain.formula ?? "无",
    chain.herb,
    chain.compound,
    chain.target,
    chain.pathway,
    chain.disease,
    formatScore(chain.score),
    formatEntityIds(chain.related_entity_ids),
  ]
    .map(escapeTableCell)
    .join(" | ");
}

export function buildNetworkReportMarkdown(
  result: NetworkAnalysisResult,
  exportedAt = new Date().toISOString(),
): string {
  const sections: string[] = [];
  sections.push("# Qiyan Nexus 网络药理学报告导出");
  sections.push("");
  sections.push(`- 导出时间（UTC）：${exportedAt}`);
  sections.push(`- task_id：${result.task_id}`);
  sections.push(`- 分析对象：${result.query}`);
  sections.push(`- 分析类型：${getNetworkAnalysisTypeLabel(result.analysis_type)}`);
  sections.push(`- 链路数量：${result.chains.length}`);
  sections.push("- 数据来源：本报告基于本地 mock seed graph 生成");
  sections.push("");
  sections.push("## 链路结果");
  sections.push("");
  if (result.chains.length === 0) {
    sections.push("（当前报告没有可导出的 mock 链路。）");
  } else {
    sections.push(
      "| 序号 | 方剂 | 单味中药 | 成分 | 靶点 | 通路 | 疾病 | Mock 置信度 | 相关实体 ID |",
    );
    sections.push("|---|---|---|---|---|---|---|---:|---|");
    result.chains.forEach((chain, index) => {
      sections.push(`| ${formatChainRow(chain, index)} |`);
    });
  }
  sections.push("");

  // Add enrichment analysis section if available
  if (result.enrichment && result.enrichment.terms.length > 0) {
    sections.push("## 富集分析结果");
    sections.push("");
    sections.push(`- 输入基因数：${result.enrichment.input_gene_count}`);
    sections.push(`- 背景基因数：${result.enrichment.background_gene_count}`);
    sections.push(`- 分析类型：${result.enrichment.analysis_type}`);
    sections.push(`- 富集通路/功能数：${result.enrichment.terms.length}`);
    sections.push("");
    sections.push("| Term ID | 通路/功能 | 类别 | 重叠基因 | P-value | 校正后 P-value | 基因列表 |");
    sections.push("|---|---|---|---:|---:|---:|---|");
    result.enrichment.terms.forEach((term) => {
      const termName = term.term_name_zh || term.term_name;
      const overlapFraction = `${term.overlap_count}/${term.gene_count}`;
      const pValue = term.p_value.toExponential(2);
      const adjPValue = term.adjusted_p_value.toExponential(2);
      const genes = term.genes.join(", ");
      sections.push(
        `| ${escapeTableCell(term.term_id)} | ${escapeTableCell(termName)} | ${escapeTableCell(term.category)} | ${escapeTableCell(overlapFraction)} | ${escapeTableCell(pValue)} | ${escapeTableCell(adjPValue)} | ${escapeTableCell(genes)} |`,
      );
    });
    sections.push("");
    sections.push("### 参数说明");
    sections.push("");
    sections.push("- **P-value**：超几何分布计算的原始 p 值");
    sections.push("- **校正后 P-value**：Bonferroni 校正后的 p 值");
    sections.push("- **重叠基因**：输入基因与该通路/功能的交集数量");
    sections.push("- **过滤条件**：p < 0.05 且重叠基因数 >= 2");
    sections.push("");
  }

  sections.push("## 网络图");
  sections.push("");
  sections.push("![成分-靶点-通路网络图](placeholder-network-graph.png)");
  sections.push("");
  sections.push("*注：图片占位符，实际图片生成功能待后续实现*");
  sections.push("");

  sections.push("## 边界说明");
  sections.push("");
  sections.push("- 不是正式网络药理学计算。");
  sections.push("- 富集分析基于本地 JSON 字典（mock），不代表真实 KEGG REST API 或 STRING 数据库。");
  sections.push("- 不构成诊断或治疗建议，实际判断需核对原始文献、参数版本与临床背景。");
  sections.push("");
  sections.push("---");
  sections.push("");
  sections.push(result.disclaimer);
  sections.push("");
  return sections.join(NEWLINE);
}

function sanitizeTaskId(taskId: string): string {
  const sanitized = taskId
    .trim()
    .replace(/[^a-zA-Z0-9_-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
  return sanitized || "network-task";
}

export function buildNetworkReportFileName(
  taskId: string,
  exportedAt = new Date().toISOString(),
): string {
  const safeTaskId = sanitizeTaskId(taskId);
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(exportedAt);
  if (!match) {
    return `qiyan-network-report-${safeTaskId}.md`;
  }
  const [, y, mo, d, h, mi] = match;
  return `qiyan-network-report-${safeTaskId}-${y}${mo}${d}-${h}${mi}.md`;
}
