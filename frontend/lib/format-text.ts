// 展示层文本截断：任务对象名等 label 可能来自历史任务或导入数据，
// 长度不受新建表单约束；列表与摘要句截断显示，完整值通过 title 保留可及性。
export function truncateLabel(value: string, maxLength = 40): string {
  const trimmed = value.trim();
  if (trimmed.length <= maxLength) {
    return trimmed;
  }
  return `${trimmed.slice(0, maxLength)}…`;
}
