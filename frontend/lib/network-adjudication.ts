import type {
  NetworkAdjudicationDecision,
  NetworkAdjudicationRecord,
  NetworkTargetLineage,
} from "./api/network";

export function getNetworkAdjudicationDecisionLabel(decision: NetworkAdjudicationDecision): string {
  switch (decision) {
    case "included":
      return "已纳入";
    case "excluded":
      return "已排除";
    default:
      return "待复核";
  }
}

export function getNetworkAdjudicationButtonLabel(decision: NetworkAdjudicationDecision): string {
  switch (decision) {
    case "included":
      return "纳入";
    case "excluded":
      return "排除";
    default:
      return "待复核";
  }
}

export function buildNetworkAdjudicationDecisionMap(
  current: NetworkAdjudicationRecord[] | null | undefined,
): Map<string, NetworkAdjudicationRecord> {
  const map = new Map<string, NetworkAdjudicationRecord>();
  for (const record of current ?? []) {
    map.set(record.lineage_row_id, record);
  }
  return map;
}

export function countNetworkLineageRows(lineage: NetworkTargetLineage): number {
  return (
    lineage.disease_lineage_row_count +
    lineage.compound_lineage_row_count +
    lineage.intersection_lineage_row_count
  );
}

export function getNetworkAdjudicationInFlightMessage(inFlightCount: number): string | null {
  if (inFlightCount <= 0) {
    return null;
  }
  return `正在提交 ${inFlightCount} 行人工判定，提交完成前这些行的按钮暂不可用。`;
}

export function getNetworkAdjudicationUnavailableReason(input: {
  taskCompleted: boolean;
  lineageRowCount: number;
}): string | null {
  if (!input.taskCompleted) {
    return "任务尚未完成，只有 completed 状态的研究任务才能进行人工判定。";
  }
  if (input.lineageRowCount === 0) {
    return "当前任务没有可判定的靶点 lineage 行，人工判定不可用。";
  }
  return null;
}
