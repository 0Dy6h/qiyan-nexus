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
        border: "1px solid #fdba74",
        borderRadius: 8,
        background: "#fff7ed",
      }}
    >
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          flexShrink: 0,
          padding: "4px 14px",
          borderRadius: 999,
          background: "#fed7aa",
          color: "#9a3412",
          fontSize: 12,
          fontWeight: 700,
          lineHeight: "20px",
        }}
      >
        演示数据
      </span>
      <div style={{ display: "grid", gap: compact ? 0 : 4 }}>
        <p style={{ color: "#9a3412", fontSize: 14, lineHeight: "22px", margin: 0 }}>
          当前为示例数据集，用于演示证据工作台骨架功能。
        </p>
        {!compact && (
          <p style={{ color: "#c2410c", fontSize: 13, lineHeight: "20px", margin: 0 }}>
            文献条目为合成构造，未对接知网/PubMed 真实库；上传 PDF 仅作解析链路演示，不进入正式索引。
          </p>
        )}
      </div>
    </section>
  );
}
