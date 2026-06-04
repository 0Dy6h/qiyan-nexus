export function buildAnswerMarkdownFileName(answeredAt: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(answeredAt);
  if (!match) {
    return "qiyan-rag-answer.md";
  }
  const [, y, mo, d, h, mi] = match;
  return `qiyan-rag-answer-${y}${mo}${d}-${h}${mi}.md`;
}
