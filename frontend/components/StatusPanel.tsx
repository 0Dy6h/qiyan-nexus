import type { CSSProperties } from "react";

import { getStatusCardStyle, getStatusMessageStyle, getStatusTone } from "../lib/ui/status-card";

type StatusPanelProps = {
  message: string;
  tone?: "idle" | "error";
};

export default function StatusPanel({ message, tone = "idle" }: StatusPanelProps) {
  const resolvedTone = getStatusTone(tone === "error");

  return (
    <div style={getStatusCardStyle(resolvedTone) as CSSProperties}>
      <p style={getStatusMessageStyle(resolvedTone) as CSSProperties}>{message}</p>
    </div>
  );
}
