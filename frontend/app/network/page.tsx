import { Suspense } from "react";

import NetworkAnalysisClient from "../../components/NetworkAnalysisClient";
import StatusPanel from "../../components/StatusPanel";
import { getComplianceNavigationLinks } from "../../lib/compliance-page";

export default function NetworkPage() {
  const navigationLinks = getComplianceNavigationLinks();

  return (
    <main className="workbench-page" style={{ minHeight: "100vh", padding: "clamp(20px, 4vw, 48px)" }}>
      <section className="workbench-frame">
        <nav aria-label="工作台导航" className="workbench-nav">
          {navigationLinks.map((link) => {
            const isCurrent = link.href === "/network";

            return (
              <a key={link.href} href={link.href} aria-current={isCurrent ? "page" : undefined}>
                {link.label}
              </a>
            );
          })}
        </nav>

        <article className="workbench-hero">
          <div className="workbench-hero-main">
            <p className="workbench-kicker">Evidence workbench</p>
            <h1 className="workbench-title">网络药理学（mock）</h1>
            <p className="workbench-summary">
              当前阶段只验证「成分-靶点-通路-疾病」任务壳与结果展示，把未来网络药理学能力预留为可审阅的机制图谱入口。
            </p>
          </div>
          <aside className="workbench-hero-aside" aria-label="网络药理学能力边界">
            <div className="workbench-stat">
              <span>Endpoints</span>
              <strong>/api/network/analyze</strong>
            </div>
            <div className="workbench-stat">
              <span>Mock chain</span>
              <strong>成分 → 靶点 → 通路</strong>
            </div>
            <div className="workbench-stat">
              <span>Phase</span>
              <strong>MVP-B concept reserve</strong>
            </div>
          </aside>
        </article>

        <div className="workbench-content-band">
          <section className="workbench-stage-note" role="note" aria-label="网络药理学演示数据说明">
            <h2>演示数据边界</h2>
            <p style={{ color: "var(--qiyan-muted)", lineHeight: 1.72 }}>
              当前网络分析使用本地 mock seed graph 和本地 GO/KEGG 演示字典，仅用于功能验证与评审走查；不可作为科研发表、临床决策或真实数据库分析结果。
            </p>
          </section>

          <Suspense fallback={<StatusPanel message="加载网药分析面板..." />}>
            <NetworkAnalysisClient />
          </Suspense>
        </div>

        <section aria-label="使用提醒" className="workbench-reminder">
          <p className="workbench-reminder-title">使用提醒</p>
          <p className="workbench-reminder-copy">
            本页面信息仅用于研究与产品能力说明，不构成诊断或治疗建议；实际判断仍需结合临床指南、原始文献与专业医生意见。
          </p>
        </section>
      </section>
    </main>
  );
}
