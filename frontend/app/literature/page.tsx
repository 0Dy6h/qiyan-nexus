import { Suspense } from "react";

import DemoDataBanner from "../../components/DemoDataBanner";
import LiteraturePubmedSyncClient from "../../components/LiteraturePubmedSyncClient";
import LiteratureSearchClient from "../../components/LiteratureSearchClient";
import StatusPanel from "../../components/StatusPanel";

export default function LiteraturePage() {
  return (
    <>
        <article className="workbench-hero">
          <div className="workbench-hero-main">
            <p className="workbench-kicker">Evidence workbench</p>
            <h1 className="workbench-title">文献检索</h1>
            <p className="workbench-summary">
              从来源、年份、摘要与 PDF 状态开始审阅，把 PubMed runtime、seed sample 与上传 PDF 放在同一套证据入口里。
            </p>
          </div>
          <aside className="workbench-hero-aside" aria-label="文献检索能力边界">
            <div className="workbench-stat">
              <span>Endpoint</span>
              <strong>/api/literature/search</strong>
            </div>
            <div className="workbench-stat">
              <span>Review order</span>
              <strong>来源 → 摘要 → PDF</strong>
            </div>
            <div className="workbench-stat">
              <span>Data scope</span>
              <strong>Seed / PubMed / Upload</strong>
            </div>
          </aside>
        </article>

        <div className="workbench-content-band">
          <DemoDataBanner />

          <LiteraturePubmedSyncClient />

          <Suspense fallback={<StatusPanel message="加载文献检索面板..." />}>
            <LiteratureSearchClient />
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
