export function getStatusTone(hasError) {
  return hasError ? "error" : "idle";
}

export function getStatusCardStyle(tone) {
  if (tone === "error") {
    return {
      background: "#fff7ed",
      border: "1px solid #fdba74",
      borderRadius: 12,
      padding: "16px 18px",
    };
  }

  return {
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: 12,
    padding: "16px 18px",
  };
}

export function getStatusMessageStyle(tone) {
  return {
    color: tone === "error" ? "#b45309" : "#64748b",
    margin: 0,
    lineHeight: 1.6,
  };
}
