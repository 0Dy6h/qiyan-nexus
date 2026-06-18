import { Suspense } from "react";

import NetworkAnalysisClient from "../../components/NetworkAnalysisClient";
import StatusPanel from "../../components/StatusPanel";

export default function NetworkPage() {
  return (
    <>
      <article className="workbench-hero">
        <div className="workbench-hero-main">
          <p className="workbench-kicker">Evidence workbench</p>
          <h1 className="workbench-title">机制线索探索（mock）</h1>
          <p className="workbench-summary">
            当前阶段只验证「成分-靶点-通路-疾病」任务壳与结果展示，把未来网络药理学能力预留为可审阅的机制图谱入口；默认结果不是正式网络药理学分析结论。
          </p>
        </div>
        <aside className="workbench-hero-aside" aria-label="机制线索能力边界">
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
        <section className="workbench-stage-note" role="note" aria-label="机制线索演示数据说明">
          <h2>演示数据边界</h2>
          <p style={{ color: "var(--qiyan-muted)", lineHeight: 1.72 }}>
            当前默认网络分析使用本地 mock seed graph 和本地 GO/KEGG
            演示字典，仅用于功能验证与评审走查；真实数据链路需显式 opt-in，且不可作为科研发表、临床决策或真实数据库分析结果，live
            结果也必须核对外部来源与缓存时间。
          </p>
        </section>

        <Suspense fallback={<StatusPanel message="加载机制线索面板..." />}>
          <NetworkAnalysisClient />
        </Suspense>
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
