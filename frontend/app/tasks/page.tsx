import { Suspense } from "react";

import NetworkTaskListClient from "../../components/NetworkTaskListClient";
import StatusPanel from "../../components/StatusPanel";

export default function TasksPage() {
  return (
    <>
      <article className="workbench-hero">
        <div className="workbench-hero-main">
          <p className="workbench-kicker">My research tasks</p>
          <h1 className="workbench-title">我的研究</h1>
          <p className="workbench-summary">
            汇总当前环境（受保护部署下为本人）的网络药理学研究任务：核对分析对象、状态、数据模式与科研就绪标记，再进入单个任务查看冻结快照、派生交集与人工判定。
          </p>
        </div>
        <aside className="workbench-hero-aside" aria-label="我的研究能力边界">
          <div className="workbench-stat">
            <span>Endpoint</span>
            <strong>/api/network/tasks</strong>
          </div>
          <div className="workbench-stat">
            <span>Scope</span>
            <strong>owner-scoped · 本地预览为全部任务</strong>
          </div>
          <div className="workbench-stat">
            <span>Order</span>
            <strong>按创建时间倒序</strong>
          </div>
        </aside>
      </article>

      <div className="workbench-content-band">
        <Suspense fallback={<StatusPanel message="加载研究任务列表..." />}>
          <NetworkTaskListClient />
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
