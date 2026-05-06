import LiteratureSearchClient from "../../components/LiteratureSearchClient";

export default function LiteraturePage() {
  return (
    <main style={{ minHeight: "100vh", background: "#f8fafc", padding: 48 }}>
      <section style={{ maxWidth: 1120, margin: "0 auto" }}>
        <a href="/" style={{ color: "#0d9488", fontWeight: 700 }}>
          ← 返回首页
        </a>
        <h1 style={{ color: "#1e293b", fontSize: 36 }}>文献检索</h1>
        <p style={{ color: "#475569", fontSize: 18 }}>
          当前页面调用后端 <code>/api/literature/search</code>，用于验证文献检索的第一条前后端链路。
        </p>
        <LiteratureSearchClient />
        <p style={{ color: "#64748b", marginTop: 32 }}>非诊断结论、需结合临床。</p>
      </section>
    </main>
  );
}
