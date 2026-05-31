export function getCompliancePageIntro() {
  return {
    eyebrow: "Qiyan Nexus · 合规说明",
    title: "合规与使用边界",
    summary:
      "说明当前证据工作台的适用对象、输出边界、引用要求、隐私处理原则、数据来源与 PDF 版权边界。",
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
        "默认 deterministic 模式完全离线，问题与引用片段不外发给任何外部服务。",
        "启用真实 LLM（QIYAN_LLM_PROVIDER=opencode_go）后，问题文本与命中的引用片段会发送至外部 OpenAI 兼容网关用于生成回答；检索、引用卡片与免责声明仍由本地后端控制。",
        "遵循 PIPL 最小必要与告知原则：仅发送回答所需的问题与引用片段，不发送患者身份信息、就诊记录或其他可识别个人信息。",
        "后续接入 PDF 或病例材料前，应先完成脱敏、权限与留痕方案。",
      ],
    },
    {
      title: "数据来源说明",
      items: [
        "中文文献部分来自 seed sample 数据集，仅作演示与开发期回归用途，不代表 CNKI / 万方等数据库授权内容。",
        "英文文献部分来自 PubMed 实时同步（NCBI E-utilities），使用须遵守 NCBI 服务条款与速率限制；同步结果会落入 runtime 状态，不会覆盖 seed。",
        "用户上传 PDF 仅保存在本地 runtime 目录，用于解析预览与证据核对，不进入任何外部检索或训练流程。",
      ],
    },
    {
      title: "PDF 版权声明",
      items: [
        "上传的 PDF 仅在本地工作台用于研究、教学与证据核对，不公开、不再分发、不上传至任何第三方服务。",
        "用户应自行确认对所上传 PDF 拥有合法访问与使用权利，版权归原出版方与作者所有。",
        "若收到权利人下架请求，应在 runtime 目录与 literature 状态中删除对应文件与解析记录。",
      ],
    },
  ];
}

export function getComplianceNavigationLinks() {
  return [
    { href: "/", label: "返回首页" },
    { href: "/literature", label: "查看文献检索" },
    { href: "/rag", label: "查看 RAG 问答" },
    { href: "/network", label: "查看网络药理学" },
    { href: "/evals/rag-ad", label: "运行 RAG 评估" },
  ];
}
