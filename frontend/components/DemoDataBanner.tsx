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
        border: "1px solid var(--qiyan-status-warning-line)",
        borderRadius: 14,
        background: "var(--qiyan-status-warning-bg)",
      }}
    >
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          flexShrink: 0,
          padding: "4px 14px",
          borderRadius: 999,
          background: "rgba(180, 83, 9, 0.12)",
          color: "var(--qiyan-status-warning-text)",
          fontSize: 12,
          fontWeight: 700,
          lineHeight: "20px",
        }}
      >
        演示数据
      </span>
      <div style={{ display: "grid", gap: compact ? 0 : 4 }}>
        <p style={{ color: "var(--qiyan-status-warning-text)", fontSize: 14, fontWeight: 700, lineHeight: "22px", margin: 0 }}>
          当前为示例数据集，用于演示证据工作台骨架功能。
        </p>
        {!compact && (
          <p style={{ color: "#7c5a10", fontSize: 13, lineHeight: "20px", margin: 0 }}>
            文献条目为小型合成样本集（当前约数十篇构造文献），未对接知网/PubMed 真实库，不可作为外部可检索的真实文献引用；上传 PDF 仅作解析链路演示，不进入正式索引。
          </p>
        )}
      </div>
    </section>
  );
}
