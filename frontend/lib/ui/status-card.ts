export type StatusTone = "idle" | "error" | "warning" | "success" | "danger";

export function getStatusTone(hasError: boolean): StatusTone {
  return hasError ? "error" : "idle";
}

export function getPdfStatusTone(status: string | null | undefined): StatusTone {
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

export function getPdfActionLabels(status: string | null | undefined): string[] {
  if (status === "pending") {
    return ["标记已解析", "标记解析失败"];
  }
  return [];
}

export function getPdfStatusCopy(
  status: string | null | undefined,
  isParsing: boolean,
  parseMessage: string | null | undefined,
): string {
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

export function getStatusCardStyle(tone: StatusTone): Record<string, string | number> {
  if (tone === "error") {
    return {
      backdropFilter: "blur(14px) saturate(135%)",
      background: "var(--qiyan-status-error-bg)",
      border: "1px solid var(--qiyan-status-error-line)",
      borderRadius: 16,
      padding: "16px 18px",
    };
  }
  if (tone === "warning") {
    return {
      backdropFilter: "blur(14px) saturate(135%)",
      background: "var(--qiyan-status-warning-bg)",
      border: "1px solid var(--qiyan-status-warning-line)",
      borderRadius: 16,
      padding: "16px 18px",
    };
  }
  if (tone === "success") {
    return {
      backdropFilter: "blur(14px) saturate(135%)",
      background: "var(--qiyan-status-success-bg)",
      border: "1px solid var(--qiyan-status-success-line)",
      borderRadius: 16,
      padding: "16px 18px",
    };
  }
  if (tone === "danger") {
    return {
      backdropFilter: "blur(14px) saturate(135%)",
      background: "var(--qiyan-status-danger-bg)",
      border: "1px solid var(--qiyan-status-danger-line)",
      borderRadius: 16,
      padding: "16px 18px",
    };
  }
  return {
    backdropFilter: "blur(14px) saturate(135%)",
    background: "var(--qiyan-status-idle-bg)",
    border: "1px solid var(--qiyan-status-idle-line)",
    borderRadius: 16,
    padding: "16px 18px",
  };
}

export function getStatusMessageStyle(tone: StatusTone): Record<string, string | number> {
  if (tone === "error") {
    return {
      color: "#fed7aa",
      margin: 0,
      lineHeight: 1.6,
    };
  }
  if (tone === "warning") {
    return {
      color: "#fde68a",
      margin: 0,
      lineHeight: 1.6,
    };
  }
  if (tone === "success") {
    return {
      color: "#99f6e4",
      margin: 0,
      lineHeight: 1.6,
    };
  }
  if (tone === "danger") {
    return {
      color: "#fecdd3",
      margin: 0,
      lineHeight: 1.6,
    };
  }
  return {
    color: "var(--qiyan-muted)",
    margin: 0,
    lineHeight: 1.6,
  };
}
