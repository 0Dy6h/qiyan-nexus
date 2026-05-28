import RagEvalReportClient from "../../../components/RagEvalReportClient";

export default function RagAdEvalPage() {
  return (
    <main style={{ minHeight: "100vh", background: "#f8fafc", padding: 48 }}>
      <section style={{ maxWidth: 1120, margin: "0 auto" }}>
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 20 }}>
          <a href="/" style={{ color: "#0d9488", fontWeight: 700, textDecoration: "none" }}>
            返回首页
          </a>
          <a href="/rag" style={{ color: "#0d9488", fontWeight: 700, textDecoration: "none" }}>
            查看 RAG 问答
          </a>
          <a href="/literature" style={{ color: "#0d9488", fontWeight: 700, textDecoration: "none" }}>
            查看文献检索
          </a>
        </div>
        <h1 style={{ color: "#1e293b", fontSize: 36 }}>RAG 评估</h1>
        <p style={{ color: "#475569", fontSize: 18, lineHeight: 1.7 }}>
          运行 50 个特应性皮炎评估问题，检查 deterministic RAG 的引用命中、chunk 命中、免责声明覆盖和禁用语风险。
        </p>
        <RagEvalReportClient />
        <p style={{ color: "#64748b", marginTop: 32 }}>非诊断结论、需结合临床。</p>
      </section>
    </main>
  );
}
