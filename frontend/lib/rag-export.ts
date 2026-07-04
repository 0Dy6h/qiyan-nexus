function buildAnswerFileName(answeredAt: string, ext: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(answeredAt);
  if (!match) {
    return `qiyan-rag-answer.${ext}`;
  }
  const [, y, mo, d, h, mi] = match;
  return `qiyan-rag-answer-${y}${mo}${d}-${h}${mi}.${ext}`;
}

export function buildAnswerMarkdownFileName(answeredAt: string): string {
  return buildAnswerFileName(answeredAt, "md");
}

export function buildAnswerDocxFileName(answeredAt: string): string {
  return buildAnswerFileName(answeredAt, "docx");
}
