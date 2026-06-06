type Props = { compact?: boolean };

export default function DemoDataBanner({ compact = false }: Props) {
  return (
    <section
      role="note"
      aria-label="演示数据提示"
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: 12,
        padding: compact ? 10 : 16,
        backdropFilter: "blur(14px) saturate(135%)",
        border: "1px solid rgba(245, 158, 11, 0.44)",
        borderRadius: 16,
        background: "rgba(36, 24, 5, 0.36)",
      }}
    >
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          flexShrink: 0,
          padding: "4px 14px",
          borderRadius: 999,
          background: "rgba(245, 158, 11, 0.18)",
          color: "#fde68a",
          fontSize: 12,
          fontWeight: 700,
          lineHeight: "20px",
        }}
      >
        演示数据
      </span>
      <div style={{ display: "grid", gap: compact ? 0 : 4 }}>
        <p style={{ color: "#fde68a", fontSize: 14, lineHeight: "22px", margin: 0 }}>
          当前为示例数据集，用于演示证据工作台骨架功能。
        </p>
        {!compact && (
          <p style={{ color: "#f9d99a", fontSize: 13, lineHeight: "20px", margin: 0 }}>
            文献条目为合成构造，未对接知网/PubMed 真实库；上传 PDF 仅作解析链路演示，不进入正式索引。
          </p>
        )}
      </div>
    </section>
  );
}
