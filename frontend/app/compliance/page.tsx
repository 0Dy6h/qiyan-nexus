import { CardBodyText } from "../../components/CardMeta";
import {
  getComplianceHighlights,
  getCompliancePageIntro,
  getCompliancePlatformScope,
  getComplianceTrustPrinciples,
} from "../../lib/compliance-page";

export default function CompliancePage() {
  const intro = getCompliancePageIntro();
  const highlights = getComplianceHighlights();
  const trustPrinciples = getComplianceTrustPrinciples();
  const platformScope = getCompliancePlatformScope();

  return (
    <>
        <article className="workbench-hero">
          <div className="workbench-hero-main">
            <p className="workbench-kicker">{intro.eyebrow}</p>
            <h1 className="workbench-title">{intro.title}</h1>
            <p className="workbench-summary">{intro.summary}</p>
          </div>
          <aside className="workbench-hero-aside" aria-label="合规说明摘要">
            <div className="workbench-stat">
              <span>Audience</span>
              <strong>医生 / 科研人员</strong>
            </div>
            <div className="workbench-stat">
              <span>Output</span>
              <strong>非诊断结论</strong>
            </div>
            <div className="workbench-stat">
              <span>Data</span>
              <strong>Seed / PubMed / PDF</strong>
            </div>
          </aside>
        </article>

        <div className="workbench-content-band">
          <section aria-label="平台合规与可信原则" style={{ display: "grid", gap: 12 }}>
            <h2 style={{ color: "var(--qiyan-ink)", fontSize: 22, margin: 0 }}>平台合规与可信原则</h2>
            <div className="compliance-grid">
              {trustPrinciples.map((principle) => (
                <article key={principle.title} className="compliance-card">
                  <h2>{principle.title}</h2>
                  <p style={{ color: "var(--qiyan-muted-2)", margin: "0 0 8px", lineHeight: 1.6 }}>
                    {principle.detail}
                  </p>
                  <p style={{ color: "var(--qiyan-muted)", margin: 0, fontSize: 13, lineHeight: 1.6 }}>
                    落地：{principle.backing}
                  </p>
                </article>
              ))}
            </div>
          </section>

          <section
            aria-label="平台定位与应用边界"
            style={{
              display: "grid",
              gap: 16,
              gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            }}
          >
            <article className="compliance-card">
              <h2>平台可以做什么</h2>
              <ul>
                {platformScope.canDo.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </article>
            <article className="compliance-card">
              <h2>平台不替代什么</h2>
              <ul>
                {platformScope.cannotReplace.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </article>
          </section>

          <div className="compliance-grid">
            {highlights.map((section) => (
              <article key={section.title} className="compliance-card">
                <h2>{section.title}</h2>
                <ul>
                  {section.items.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </article>
            ))}
          </div>

          <section className="workbench-stage-note">
            <div style={{ display: "grid", gap: 8 }}>
              <h2>当前阶段说明</h2>
              <CardBodyText>
                当前版本用于验证 AD 证据工作台的最小前后端链路，重点覆盖文献检索、RAG 问答、citation cards 与 PDF
                upload/mock parse 的工程骨架，不代表已接入真实诊疗、真实解析或真实模型推理能力。
              </CardBodyText>
            </div>
          </section>
        </div>

        <section aria-label="使用提醒" className="workbench-reminder">
          <p className="workbench-reminder-title">使用提醒</p>
          <p className="workbench-reminder-copy">
            本页面信息仅用于研究与产品能力说明，不构成诊断或治疗建议；实际判断仍需结合临床指南、原始文献与专业医生意见。
          </p>
        </section>
    </>
  );
}
