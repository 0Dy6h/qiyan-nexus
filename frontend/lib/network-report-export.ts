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
