import {
  getNetworkAnalysisTypeLabel,
  getNetworkDataModeLabel,
  getNetworkTaskReadinessLabel,
  getNetworkTaskStatusLabel,
  type NetworkTaskSummary,
} from "./api/network";

export function parseNetworkTaskIdParam(value: string | null): string | null {
  const trimmed = value?.trim() ?? "";
  return trimmed.length > 0 ? trimmed : null;
}

export function formatNetworkTaskCreatedAt(createdAt: string): string {
  const trimmed = createdAt.trim();
  if (!trimmed) {
    return "未知时间";
  }
  return trimmed.replace("T", " ").slice(0, 16);
}

export function buildNetworkTaskViewHref(taskId: string): string {
  return `/network?task_id=${encodeURIComponent(taskId)}`;
}

export type NetworkTaskListRow = {
  taskId: string;
  sourceTaskId: string | null;
  isDerived: boolean;
  query: string;
  analysisTypeLabel: string;
  statusLabel: string;
  status: NetworkTaskSummary["status"];
  dataModeLabel: string;
  dataMode: NetworkTaskSummary["data_mode"];
  readinessLabel: string;
  formalNetworkReady: boolean;
  createdAtLabel: string;
  viewHref: string;
};

export function mapNetworkTaskToRow(task: NetworkTaskSummary): NetworkTaskListRow {
  return {
    taskId: task.task_id,
    sourceTaskId: task.source_task_id,
    isDerived: Boolean(task.source_task_id),
    query: task.query,
    analysisTypeLabel: getNetworkAnalysisTypeLabel(task.analysis_type),
    statusLabel: getNetworkTaskStatusLabel(task.status),
    status: task.status,
    dataModeLabel: getNetworkDataModeLabel(task.data_mode),
    dataMode: task.data_mode,
    readinessLabel: getNetworkTaskReadinessLabel(task.formal_network_ready),
    formalNetworkReady: task.formal_network_ready,
    createdAtLabel: formatNetworkTaskCreatedAt(task.created_at),
    viewHref: buildNetworkTaskViewHref(task.task_id),
  };
}

export function mapNetworkTasksToRows(tasks: NetworkTaskSummary[]): NetworkTaskListRow[] {
  return tasks.map(mapNetworkTaskToRow);
}
