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
      background: "#fff7ed",
      border: "1px solid #fdba74",
      borderRadius: 8,
      padding: "16px 18px",
    };
  }
  if (tone === "warning") {
    return {
      background: "#fffbeb",
      border: "1px solid #facc15",
      borderRadius: 8,
      padding: "16px 18px",
    };
  }
  if (tone === "success") {
    return {
      background: "#f0fdfa",
      border: "1px solid #99f6e4",
      borderRadius: 8,
      padding: "16px 18px",
    };
  }
  if (tone === "danger") {
    return {
      background: "#fef2f2",
      border: "1px solid #fecaca",
      borderRadius: 8,
      padding: "16px 18px",
    };
  }
  return {
    background: "#f8fafc",
    border: "1px solid #dbe7e3",
    borderRadius: 8,
    padding: "16px 18px",
  };
}

export function getStatusMessageStyle(tone: StatusTone): Record<string, string | number> {
  if (tone === "error") {
    return {
      color: "#b45309",
      margin: 0,
      lineHeight: 1.6,
    };
  }
  if (tone === "warning") {
    return {
      color: "#92400e",
      margin: 0,
      lineHeight: 1.6,
    };
  }
  if (tone === "success") {
    return {
      color: "#0f766e",
      margin: 0,
      lineHeight: 1.6,
    };
  }
  if (tone === "danger") {
    return {
      color: "#991b1b",
      margin: 0,
      lineHeight: 1.6,
    };
  }
  return {
    color: "#5f6e68",
    margin: 0,
    lineHeight: 1.6,
  };
}
