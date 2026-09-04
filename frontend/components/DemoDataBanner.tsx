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
          数据边界提示：演示 seed 与实时记录分开标注，引用前先核对每张卡片的记录来源。
        </p>
        {!compact && (
          <p style={{ color: "#7c5a10", fontSize: 13, lineHeight: "20px", margin: 0 }}>
            中文文献为小型合成 seed 样本，未对接知网/万方真实授权数据库；PubMed 记录来自 NCBI E-utilities 实时同步，须遵守 NCBI 服务条款与速率限制；上传 PDF 仅保存在本地 runtime 作解析链路演示。演示 seed 样本不可当作外部可检索的真实文献引用。
          </p>
        )}
      </div>
    </section>
  );
}
