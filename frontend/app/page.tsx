import type { ReactNode } from "react";
import {
  ArrowRightOutlined,
  BranchesOutlined,
  ExperimentOutlined,
  FileSearchOutlined,
  SafetyCertificateOutlined,
} from "@ant-design/icons";

const DISCLAIMER = "非诊断结论、需结合临床。";

const taskCards: Array<{
  href: string;
  icon: ReactNode;
  eyebrow: string;
  title: string;
  body: string;
  metric: string;
}> = [
  {
    href: "/network",
    icon: <BranchesOutlined aria-hidden="true" />,
    eyebrow: "Step 1",
    title: "定研究协议",
    body: "冻结方药对象、明确 AD 表型、物种、证据策略与查询日期，拒绝宽泛 disease target union。",
    metric: "Protocol gate",
  },
  {
    href: "/network",
    icon: <BranchesOutlined aria-hidden="true" />,
    eyebrow: "Step 2",
    title: "构建网络",
    body: "按研究协议组织方药-成分-靶点-通路链，保留来源、版本、阈值、缓存与证据等级。",
    metric: "Edges / PPI / Enrichment",
  },
  {
    href: "/literature",
    icon: <FileSearchOutlined aria-hidden="true" />,
    eyebrow: "Step 3",
    title: "核证据",
    body: "用文献检索、PDF 归档和引用问答核验靶点、通路与机制边，自动提取和人工判定保持分离。",
    metric: "Literature / PDF / RAG",
  },
  {
    href: "/network",
    icon: <ExperimentOutlined aria-hidden="true" />,
    eyebrow: "Step 4",
    title: "出研究报告",
    body: "导出研究协议、来源边界、链路、富集、阻塞项与免责声明；artifact consistency 和 scientific readiness 分开报告。",
    metric: "Auditable report",
  },
];

const controlRows = [
  { label: "Scope", value: "特应性皮炎", note: "AD only" },
  { label: "Audience", value: "医生 / 科研人员", note: "非 C 端" },
  { label: "Primary", value: "网络药理学科研辅助", note: "主轴" },
  { label: "Evidence", value: "文献 / PDF / RAG", note: "服务层" },
  { label: "Readiness", value: "Scientific readiness = false", note: "默认 fail closed" },
];

const signalCards = [
  { value: "AD only", label: "窄病种边界" },
  { value: "Protocol", label: "运行前冻结研究参数" },
  { value: "Edge lineage", label: "逐边来源与证据分级" },
  { value: "Fail closed", label: "科研就绪门禁" },
  { value: DISCLAIMER, label: "输出边界" },
];

function TaskCard({ card }: Readonly<{ card: (typeof taskCards)[number] }>) {
  return (
    <a className="task-card" href={card.href}>
      <span className="task-icon">{card.icon}</span>
      <span className="task-eyebrow">{card.eyebrow}</span>
      <h3>{card.title}</h3>
      <p>{card.body}</p>
      <span className="task-foot">
        <span>{card.metric}</span>
        <ArrowRightOutlined aria-hidden="true" />
      </span>
    </a>
  );
}

export default function HomePage() {
  return (
    <>
      <article className="home-hero" aria-label="Qiyan Nexus 首页">
        <div className="home-hero-main">
          <p className="workbench-kicker">Network pharmacology research operating layer</p>
          <h1 className="home-title">窄领域网络药理学科研工作台</h1>
          <p className="home-summary">
            围绕特应性皮炎中医药研究，先冻结研究协议，再构建可追溯的成分-靶点-通路网络。文献检索、PDF 归档与 RAG 问答是证据服务层，用来核验科研链路，而不是另一个聊天产品。
          </p>

          <div className="home-app-console">
            <nav className="home-mode-tabs" aria-label="研究工作模式">
              <a className="home-mode-tab home-mode-tab-active" href="/network">
                <BranchesOutlined aria-hidden="true" />
                网络药理学研究
              </a>
              <a className="home-mode-tab" href="/literature">
                <FileSearchOutlined aria-hidden="true" />
                证据服务
              </a>
            </nav>

            <div className="home-prompt-card" aria-label="新建网络药理学研究任务">
              <div>
                <strong>从一个可证伪的研究协议开始</strong>
                <p>方药对象 → AD 明确表型 → 人类物种 → 证据策略 → 查询日期</p>
              </div>
              <div className="home-prompt-tools">
                <a className="home-send-button" href="/network" aria-label="新建网络药理学研究任务">
                  <ArrowRightOutlined aria-hidden="true" />
                </a>
              </div>
            </div>
          </div>
        </div>

        <aside className="home-boundary-panel" aria-label="当前产品边界摘要">
          <div>
            <span>Primary</span>
            <strong>网络药理学科研链路</strong>
          </div>
          <div>
            <span>Gate 1</span>
            <strong>研究协议已进入 API</strong>
          </div>
          <div>
            <span>Default</span>
            <strong>Mock + fail-closed readiness</strong>
          </div>
        </aside>
      </article>

      <section className="home-signal-strip" aria-label="科研链路概览">
        {signalCards.map((card) => (
          <article className="home-signal-card" key={card.label}>
            <strong>{card.value}</strong>
            <span>{card.label}</span>
          </article>
        ))}
      </section>

      <section className="workbench-content-band" aria-label="工作台任务入口">
        <div className="home-section-head">
          <div>
            <p className="workbench-kicker">Core research workflow</p>
            <h2>网络药理学是主流程，证据能力为每条科研链路服务</h2>
          </div>
          <p>
            主路径固定为：定研究协议 → 构建网络 → 核证据 → 出研究报告。任何上游门禁失败，都必须阻断下游科研结论。
          </p>
        </div>

        <div className="task-grid">
          {taskCards.map((card) => (
            <TaskCard key={`${card.eyebrow}-${card.title}`} card={card} />
          ))}
        </div>

        <section className="home-control-panel" aria-label="产品边界">
          <div className="home-control-intro">
            <SafetyCertificateOutlined aria-hidden="true" />
            <div>
              <h2>边界可见，结论才可信</h2>
              <p>
                当前版本建立可审计的科研工作流与失败关闭门禁；mock 结果不代表真实网络药理学发现，也不替代诊断、处方或个体治疗判断。
                <strong>{DISCLAIMER}</strong>
              </p>
            </div>
          </div>

          <dl className="home-control-table">
            {controlRows.map((row) => (
              <div className="home-control-row" key={row.label}>
                <dt>{row.label}</dt>
                <dd>{row.value}</dd>
                <dd>{row.note}</dd>
              </div>
            ))}
          </dl>
        </section>
      </section>
    </>
  );
}
