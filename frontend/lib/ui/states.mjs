export function getStatusCopy(page, isLoading) {
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

export function getEmptyStateCopy(page) {
  if (page === "rag") {
    return {
      idle: "提交问题后，从后端 /api/rag/answer 获取 mock 回答与 citation cards。",
      error: "请求失败，请确认后端服务已启动。",
    };
  }

  return {
    idle: "提交检索后，从后端 API 获取文献结果。",
    error: "检索失败，请确认后端服务已启动。",
  };
}
