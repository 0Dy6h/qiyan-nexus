import { CardBodyText } from "../../components/CardMeta";
import { getComplianceHighlights, getCompliancePageIntro } from "../../lib/compliance-page";

export default function CompliancePage() {
  const intro = getCompliancePageIntro();
  const highlights = getComplianceHighlights();

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
