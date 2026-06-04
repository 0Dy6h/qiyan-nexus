import { Suspense } from "react";

import RagAnswerClient from "../../components/RagAnswerClient";
import StatusPanel from "../../components/StatusPanel";
import { getComplianceNavigationLinks } from "../../lib/compliance-page";

export default function RagPage() {
  const navigationLinks = getComplianceNavigationLinks();

  return (
    <main className="workbench-page" style={{ minHeight: "100vh", padding: "clamp(20px, 4vw, 48px)" }}>
      <section className="workbench-frame">
        <nav aria-label="工作台导航" className="workbench-nav">
          {navigationLinks.map((link) => {
            const isCurrent = link.href === "/rag";

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
            <h1 className="workbench-title">RAG 问答</h1>
            <p className="workbench-summary">
              把问题、检索来源、top_k、grounding 与 citation cards 放在同一张审计桌面上，先读结论，再核对证据边界。
            </p>
          </div>
          <aside className="workbench-hero-aside" aria-label="RAG 问答能力边界">
            <div className="workbench-stat">
              <span>Endpoint</span>
              <strong>/api/rag/answer</strong>
            </div>
            <div className="workbench-stat">
              <span>Trace</span>
              <strong>Question → Citations</strong>
            </div>
            <div className="workbench-stat">
              <span>Control</span>
              <strong>Source / top_k / grounding</strong>
            </div>
          </aside>
        </article>

        <div className="workbench-content-band">
          <Suspense fallback={<StatusPanel message="加载 RAG 问答面板..." />}>
            <RagAnswerClient />
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
