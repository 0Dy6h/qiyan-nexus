export function getStatusTone(hasError) {
  return hasError ? "error" : "idle";
}

export function getPdfStatusTone(status) {
  if (status === "pending") {
    return "warning";
  }
  if (status === "parsed") {
    return "success";
  }
  if (status === "failed") {
    return "danger";
  }
  return "idle";
}

export function getPdfActionLabels(status) {
  if (status === "pending") {
    return ["标记已解析", "标记解析失败"];
  }
  return [];
}

export function getPdfStatusCopy(status, isParsing, parseMessage) {
  if (isParsing) {
    return "解析中...";
  }
  if (parseMessage) {
    return parseMessage;
  }
  if (status === "pending") {
    return "待解析";
  }
  if (status === "parsed") {
    return "已解析";
  }
  if (status === "failed") {
    return "解析失败";
  }
  return "尚未上传 PDF";
}

export function getStatusCardStyle(tone) {
  if (tone === "error") {
    return {
      background: "#fff7ed",
      border: "1px solid #fdba74",
      borderRadius: 12,
      padding: "16px 18px",
    };
  }
  return {
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: 12,
    padding: "16px 18px",
  };
}

export function getStatusMessageStyle(tone) {
  if (tone === "error") {
    return {
      color: "#b45309",
      margin: 0,
      lineHeight: 1.6,
    };
  }
  return {
    color: "#64748b",
    margin: 0,
    lineHeight: 1.6,
  };
}
