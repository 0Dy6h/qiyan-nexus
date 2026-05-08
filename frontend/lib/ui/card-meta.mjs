export function joinMetaItems(items) {
  return items.filter((item) => Boolean(item && item.trim())).join(" · ");
}

export function getMetaRowStyle() {
  return {
    color: "#64748b",
    margin: 0,
    fontSize: 14,
    lineHeight: 1.6,
  };
}

export function getMetaTextStyle() {
  return {
    color: "#475569",
    margin: "0 0 12px",
    lineHeight: 1.7,
  };
}
