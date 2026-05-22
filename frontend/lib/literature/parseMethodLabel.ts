const METHOD_LABEL_MAP: Record<string, string> = {
  "pypdf-text-preview": "pypdf 文本预览",
  "file-metadata-placeholder": "文件级占位",
};

export function getParseMethodLabel(method: string): string {
  return METHOD_LABEL_MAP[method] ?? method;
}
