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
        <p style={{ color: "#0d9488", fontWeight: 700 }}>AD 专病科研工作台</p>
        <h1 style={{ color: "#1e293b", fontSize: 40, lineHeight: 1.2 }}>
          中医药精准诊疗与科研一体化平台
        </h1>
        <p style={{ color: "#475569", fontSize: 18 }}>
          面向医生与科研人员，围绕特应性皮炎提供文献检索、RAG 问答、网络药理学分析与知识图谱能力。
        </p>
        <p style={{ color: "#64748b" }}>非诊断结论、需结合临床。</p>
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
      </section>
    </main>
  );
}
