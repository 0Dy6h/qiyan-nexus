import { CardBodyText } from "../../components/CardMeta";
import { getComplianceHighlights, getComplianceNavigationLinks, getCompliancePageIntro } from "../../lib/compliance-page";
import { getSurfaceCardStyle, getSurfaceSectionStyle } from "../../lib/ui/surfaces";

export default function CompliancePage() {
  const intro = getCompliancePageIntro();
  const highlights = getComplianceHighlights();
  const navigationLinks = getComplianceNavigationLinks();

  return (
    <main style={{ minHeight: "100vh", background: "#f8fafc", padding: "clamp(20px, 4vw, 48px)" }}>
      <section style={{ maxWidth: 960, margin: "0 auto", display: "grid", gap: 20 }}>
        <article style={getSurfaceSectionStyle()}>
          <div style={{ display: "grid", gap: 8 }}>
            <p style={{ color: "#0d9488", fontWeight: 700, margin: 0 }}>{intro.eyebrow}</p>
            <h1 style={{ color: "#1e293b", fontSize: 36, lineHeight: 1.2, margin: 0 }}>{intro.title}</h1>
            <p style={{ color: "#64748b", fontSize: 17, lineHeight: 1.7, margin: 0 }}>{intro.summary}</p>
          </div>
        </article>

        <nav aria-label="工作台导航" style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          {navigationLinks.map((link) => {
            const isCurrent = link.href === "/compliance";

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

        <div style={{ display: "grid", gap: 16 }}>
          {highlights.map((section) => (
            <article key={section.title} style={getSurfaceCardStyle()}>
              <h2 style={{ color: "#1e293b", fontSize: 22, marginTop: 0, marginBottom: 12 }}>{section.title}</h2>
              <ul style={{ margin: 0, paddingLeft: 20, color: "#334155", lineHeight: 1.8 }}>
                {section.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>

        <section
          style={{
            ...getSurfaceSectionStyle(),
            background: "#f0fdfa",
            border: "1px solid #99f6e4",
          }}
        >
          <div style={{ display: "grid", gap: 8 }}>
            <h2 style={{ color: "#115e59", fontSize: 20, margin: 0 }}>当前阶段说明</h2>
            <CardBodyText>
              当前版本用于验证 AD 证据工作台的最小前后端链路，重点覆盖文献检索、RAG 问答、citation cards 与 PDF
              upload/mock parse 的工程骨架，不代表已接入真实诊疗、真实解析或真实模型推理能力。
            </CardBodyText>
          </div>
        </section>

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
