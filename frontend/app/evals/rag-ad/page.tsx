import RagEvalReportClient from "../../../components/RagEvalReportClient";
import { getComplianceNavigationLinks } from "../../../lib/compliance-page";

export default function RagAdEvalPage() {
  const navigationLinks = getComplianceNavigationLinks();

  return (
    <main className="workbench-page" style={{ minHeight: "100vh", padding: "clamp(20px, 4vw, 48px)" }}>
      <section className="workbench-frame">
        <nav aria-label="工作台导航" className="workbench-nav">
          {navigationLinks.map((link) => {
            const isCurrent = link.href === "/evals/rag-ad";

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
            <h1 className="workbench-title">RAG 评估</h1>
            <p className="workbench-summary">
              运行 50 个特应性皮炎评估问题，检查 deterministic RAG 的引用命中、chunk 命中、免责声明覆盖和禁用语风险。
            </p>
          </div>
          <aside className="workbench-hero-aside" aria-label="RAG 评估边界">
            <div className="workbench-stat">
              <span>Dataset</span>
              <strong>50 AD questions</strong>
            </div>
            <div className="workbench-stat">
              <span>Checks</span>
              <strong>citations / chunks</strong>
            </div>
            <div className="workbench-stat">
              <span>Gate</span>
              <strong>disclaimer / forbidden terms</strong>
            </div>
          </aside>
        </article>

        <div className="workbench-content-band">
          <RagEvalReportClient />
        </div>

        <section aria-label="使用提醒" className="workbench-reminder">
          <p className="workbench-reminder-title">使用提醒</p>
          <p className="workbench-reminder-copy">
            非诊断结论、需结合临床。本评估仅用于产品回归与证据链路质量检查，不代表真实临床有效性结论。
          </p>
        </section>
      </section>
    </main>
  );
}
