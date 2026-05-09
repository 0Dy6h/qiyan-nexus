import {
  getComplianceHighlights,
  getComplianceNavigationLinks,
  getCompliancePageIntro,
} from "../../lib/compliance-page";

export default function CompliancePage() {
  const intro = getCompliancePageIntro();
  const links = getComplianceNavigationLinks();
  const sections = getComplianceHighlights();

  return (
    <main style={{ minHeight: "100vh", background: "#f8fafc", padding: 48 }}>
      <section style={{ maxWidth: 1040, margin: "0 auto" }}>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 20 }}>
          {links.map((link) => (
            <a key={link.href} href={link.href} style={{ color: "#0d9488", fontWeight: 700, textDecoration: "none" }}>
              {link.label}
            </a>
          ))}
        </div>

        <div
          style={{
            background: "white",
            border: "1px solid #e2e8f0",
            borderRadius: 20,
            padding: 32,
            boxShadow: "0 8px 24px rgba(15, 23, 42, 0.04)",
          }}
        >
          <p style={{ color: "#0d9488", fontWeight: 700, marginTop: 0 }}>{intro.eyebrow}</p>
          <h1 style={{ color: "#1e293b", fontSize: 36, marginBottom: 12 }}>{intro.title}</h1>
          <p style={{ color: "#475569", fontSize: 18, lineHeight: 1.7, marginTop: 0 }}>{intro.summary}</p>

          <div style={{ display: "grid", gap: 16, marginTop: 28 }}>
            {sections.map((section) => (
              <article
                key={section.title}
                style={{
                  borderRadius: 16,
                  border: "1px solid #dbeafe",
                  background: "#f8fafc",
                  padding: 20,
                }}
              >
                <h2 style={{ color: "#1e293b", fontSize: 22, marginTop: 0 }}>{section.title}</h2>
                <ul style={{ color: "#475569", lineHeight: 1.8, paddingLeft: 20, marginBottom: 0 }}>
                  {section.items.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </article>
            ))}
          </div>

          <p style={{ color: "#64748b", marginTop: 28, marginBottom: 0 }}>
            非诊断结论、需结合临床。
          </p>
        </div>
      </section>
    </main>
  );
}
