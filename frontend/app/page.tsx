export default function HomePage() {
  return (
    <main style={{ minHeight: "100vh", background: "#f8fafc", padding: 48 }}>
      <section
        style={{
          maxWidth: 960,
          margin: "0 auto",
          borderRadius: 16,
          background: "white",
          border: "1px solid #e2e8f0",
          padding: 40,
        }}
      >
        <p style={{ color: "#0d9488", fontWeight: 700 }}>Qiyan Nexus · AD 专病科研工作台</p>
        <h1 style={{ color: "#1e293b", fontSize: 40, lineHeight: 1.2 }}>
          面向特应性皮炎的中医药证据与科研工作台
        </h1>
        <p style={{ color: "#475569", fontSize: 18 }}>
          面向医生与科研人员，围绕特应性皮炎提供文献检索、RAG 问答、网络药理学分析与知识图谱能力。
        </p>
        <p style={{ color: "#64748b" }}>非诊断结论、需结合临床。</p>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <a
            href="/literature"
            style={{
              display: "inline-block",
              borderRadius: 8,
              background: "#0d9488",
              color: "white",
              fontSize: 16,
              fontWeight: 700,
              padding: "12px 20px",
              textDecoration: "none",
            }}
          >
            进入文献检索
          </a>
          <a
            href="/rag"
            style={{
              display: "inline-block",
              borderRadius: 8,
              background: "#ecfeff",
              border: "1px solid #99f6e4",
              color: "#115e59",
              fontSize: 16,
              fontWeight: 700,
              padding: "12px 20px",
              textDecoration: "none",
            }}
          >
            进入 RAG 问答
          </a>
          <a
            href="/compliance"
            style={{
              display: "inline-block",
              borderRadius: 8,
              background: "#f8fafc",
              border: "1px solid #cbd5e1",
              color: "#334155",
              fontSize: 16,
              fontWeight: 700,
              padding: "12px 20px",
              textDecoration: "none",
            }}
          >
            查看合规说明
          </a>
        </div>
      </section>
    </main>
  );
}
