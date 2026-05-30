import assert from "node:assert/strict";
import { test } from "node:test";

import type { NetworkAnalysisResult } from "../lib/api/network";
import {
  buildNetworkReportFileName,
  buildNetworkReportMarkdown,
} from "../lib/network-report-export";

const SAMPLE_RESULT: NetworkAnalysisResult = {
  task_id: "network-abc123",
  query: "消风散",
  analysis_type: "formula",
  disclaimer: "非诊断结论、需结合临床。",
  chains: [
    {
      formula: "消风散",
      herb: "荆芥",
      compound: "槲皮素",
      target: "IL6",
      pathway: "PI3K-Akt signaling pathway",
      disease: "Atopic dermatitis",
      score: 0.87,
      related_entity_ids: [
        "herb-jingjie",
        "compound-quercetin",
        "target-il6",
        "pathway-pi3k-akt",
      ],
    },
    {
      formula: "消风散",
      herb: "防风",
      compound: "木犀草素",
      target: "TNF",
      pathway: "NF-kappa B signaling pathway",
      disease: "Atopic dermatitis",
      score: 0.82,
      related_entity_ids: ["herb-fangfeng", "compound-luteolin", "target-tnf"],
    },
  ],
};

test("buildNetworkReportMarkdown exports completed network result with chains and boundaries", () => {
  const markdown = buildNetworkReportMarkdown(
    SAMPLE_RESULT,
    "2026-05-30T01:02:03.000Z",
  );

  assert.match(markdown, /^# Qiyan Nexus 网络药理学报告导出/);
  assert.ok(markdown.includes("导出时间（UTC）：2026-05-30T01:02:03.000Z"));
  assert.ok(markdown.includes("task_id：network-abc123"));
  assert.ok(markdown.includes("分析对象：消风散"));
  assert.ok(markdown.includes("分析类型：复方"));
  assert.ok(markdown.includes("链路数量：2"));
  assert.ok(markdown.includes("本报告基于本地 mock seed graph 生成"));
  assert.ok(
    markdown.includes(
      "| 序号 | 方剂 | 单味中药 | 成分 | 靶点 | 通路 | 疾病 | Mock 置信度 | 相关实体 ID |",
    ),
  );
  assert.ok(
    markdown.includes(
      "| 1 | 消风散 | 荆芥 | 槲皮素 | IL6 | PI3K-Akt signaling pathway | Atopic dermatitis | 87% | herb-jingjie, compound-quercetin, target-il6, pathway-pi3k-akt |",
    ),
  );
  assert.ok(markdown.includes("不是正式网络药理学计算"));
  assert.ok(markdown.includes("不代表 TCMSP / STRING / KEGG / GO 富集结果"));
  assert.ok(markdown.includes("非诊断结论、需结合临床。"));
});

test("buildNetworkReportMarkdown emits an empty-chain placeholder", () => {
  const markdown = buildNetworkReportMarkdown(
    { ...SAMPLE_RESULT, chains: [] },
    "2026-05-30T01:02:03.000Z",
  );

  assert.ok(markdown.includes("链路数量：0"));
  assert.ok(markdown.includes("（当前报告没有可导出的 mock 链路。）"));
  assert.ok(markdown.includes("非诊断结论、需结合临床。"));
});

test("buildNetworkReportFileName uses sanitized task id and UTC timestamp", () => {
  assert.equal(
    buildNetworkReportFileName("network-abc123", "2026-05-30T01:02:03.000Z"),
    "qiyan-network-report-network-abc123-20260530-0102.md",
  );
});

test("buildNetworkReportFileName falls back when timestamp is malformed", () => {
  assert.equal(
    buildNetworkReportFileName("network/abc 123", "not-an-iso-timestamp"),
    "qiyan-network-report-network-abc-123.md",
  );
});
