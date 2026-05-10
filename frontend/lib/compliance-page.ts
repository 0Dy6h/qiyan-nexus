export function getCompliancePageIntro() {
  return {
    eyebrow: "Qiyan Nexus · 合规说明",
    title: "合规与使用边界",
    summary: "说明当前证据工作台的适用对象、输出边界、引用要求与隐私处理原则。",
  };
}

export function getComplianceHighlights() {
  return [
    {
      title: "适用对象",
      items: [
        "当前版本仅面向医生、科研助理、研究生与 PI/方法学合作者使用。",
        "本平台不面向普通患者 C 端，也不替代线下门诊或正式会诊。",
      ],
    },
    {
      title: "输出边界",
      items: [
        "所有 AI 输出均为非诊断结论，需结合临床判断。 ",
        "当前 RAG 与证据整理功能用于研究线索汇总，不提供个体化处方、剂量或停药建议。",
      ],
    },
    {
      title: "引用与证据",
      items: [
        "引用回答时应保留文献来源、证据片段与免责声明。",
        "若 citation cards 为空或证据不足，应回到文献检索页进一步核对原文。",
      ],
    },
    {
      title: "隐私与数据处理",
      items: [
        "当前 MVP-A 不要求上传患者隐私数据开展问答。",
        "后续接入 PDF 或病例材料前，应先完成脱敏、权限与留痕方案。",
      ],
    },
  ];
}

export function getComplianceNavigationLinks() {
  return [
    { href: "/", label: "返回首页" },
    { href: "/literature", label: "查看文献检索" },
    { href: "/rag", label: "查看 RAG 问答" },
    { href: "/evals/rag-ad", label: "运行 RAG 评估" },
  ];
}
