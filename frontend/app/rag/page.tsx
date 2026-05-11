import RagAnswerClient from "../../components/RagAnswerClient";
import { getSurfaceSectionStyle } from "../../lib/ui/surfaces";

export default function RagPage() {
  return (
    <main style={{ minHeight: "100vh", background: "#f8fafc", padding: 48 }}>
      <section style={{ maxWidth: 1120, margin: "0 auto", display: "grid", gap: 20 }}>
        <a href="/" style={{ color: "#0d9488", fontWeight: 700 }}>
          ← 返回首页
        </a>

        <article style={getSurfaceSectionStyle()}>
          <div style={{ display: "grid", gap: 8 }}>
            <h1 style={{ color: "#1e293b", fontSize: 36, lineHeight: 1.3, margin: 0 }}>RAG 问答</h1>
            <p style={{ color: "#64748b", fontSize: 17, lineHeight: 1.7, margin: 0 }}>
              当前页面调用后端 <code>/api/rag/answer</code>，用于验证问答、检索元数据与 citation cards 的第一条前后端链路。
            </p>
          </div>
        </article>

        <RagAnswerClient />

        <p style={{ color: "#64748b", margin: 0 }}>非诊断结论、需结合临床。</p>
      </section>
    </main>
  );
}
