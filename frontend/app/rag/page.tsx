import RagAnswerClient from "../../components/RagAnswerClient";
import { getComplianceNavigationLinks } from "../../lib/compliance-page";
import { getSurfaceSectionStyle } from "../../lib/ui/surfaces";

export default function RagPage() {
  const navigationLinks = getComplianceNavigationLinks();

  return (
    <main style={{ minHeight: "100vh", background: "#f8fafc", padding: "clamp(20px, 4vw, 48px)" }}>
      <section style={{ maxWidth: 1120, margin: "0 auto", display: "grid", gap: 20 }}>
        <nav aria-label="工作台导航" style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          {navigationLinks.map((link) => {
            const isCurrent = link.href === "/rag";

            return (
              <a
                key={link.href}
                href={link.href}
                aria-current={isCurrent ? "page" : undefined}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  borderRadius: 999,
                  background: isCurrent ? "#ecfeff" : "transparent",
                  border: `1px solid ${isCurrent ? "#99f6e4" : "#cbd5e1"}`,
                  color: isCurrent ? "#115e59" : "#475569",
                  fontSize: 14,
                  fontWeight: isCurrent ? 700 : 600,
                  padding: "10px 14px",
                  textDecoration: "none",
                  minHeight: 44,
                }}
              >
                {link.label}
              </a>
            );
          })}
        </nav>

        <article style={getSurfaceSectionStyle()}>
          <div style={{ display: "grid", gap: 8 }}>
            <p style={{ color: "#0d9488", fontWeight: 700, margin: 0 }}>Evidence workbench</p>
            <h1 style={{ color: "#1e293b", fontSize: 36, lineHeight: 1.3, margin: 0 }}>RAG 问答</h1>
            <p style={{ color: "#64748b", fontSize: 17, lineHeight: 1.7, margin: 0 }}>
              当前页面调用后端 <code>/api/rag/answer</code>，用于验证问答、检索元数据与 citation cards 的第一条前后端链路。
            </p>
          </div>
        </article>

        <RagAnswerClient />

        <section
          aria-label="使用提醒"
          style={{
            ...getSurfaceSectionStyle(),
            background: "#f8fafc",
            border: "1px solid #e2e8f0",
            padding: 20,
          }}
        >
          <div style={{ display: "grid", gap: 6 }}>
            <p style={{ color: "#334155", fontSize: 14, fontWeight: 700, margin: 0 }}>使用提醒</p>
            <p style={{ color: "#64748b", fontSize: 14, lineHeight: 1.7, margin: 0 }}>
              本页面信息仅用于研究与产品能力说明，不构成诊断或治疗建议；实际判断仍需结合临床指南、原始文献与专业医生意见。
            </p>
          </div>
        </section>
      </section>
    </main>
  );
}
