export type StatusPage = "literature" | "rag";

export type StatusCopy = {
  submitLabel: string;
  loadingLabel: string;
};

export type EmptyStateCopy = {
  idle: string;
  error: string;
};

export function getCitationEmptyCopy() {
  return "当前回答未返回可展示的引用卡片，请调整问题或来源后重试。";
}

export function getStatusCopy(page: StatusPage, isLoading: boolean): StatusCopy {
  if (page === "rag") {
    return {
      submitLabel: "生成回答",
      loadingLabel: isLoading ? "生成中..." : "生成回答",
    };
  }

  return {
    submitLabel: "开始检索",
    loadingLabel: isLoading ? "检索中..." : "开始检索",
  };
}

export function getEmptyStateCopy(page: StatusPage): EmptyStateCopy {
  if (page === "rag") {
    return {
      idle: "基于已检索到的文献证据提问，系统会给出附引用来源的证据简报。例如：消风散对特应性皮炎皮肤屏障功能有什么影响？",
      error: "请求失败，请确认后端服务已启动。",
    };
  }

  return {
    idle: "输入中医药或疾病相关关键词，检索 AD 证据文献。例如：特应性皮炎、消风散、肠道菌群。",
    error: "检索失败，请确认后端服务已启动。",
  };
}
