import type { ReactNode } from "react";
import {
  ArrowRightOutlined,
  AuditOutlined,
  BranchesOutlined,
  ExperimentOutlined,
  FileSearchOutlined,
  QuestionCircleOutlined,
  SafetyCertificateOutlined,
} from "@ant-design/icons";

const DISCLAIMER = "非诊断结论、需结合临床。";

const navItems = [
  { href: "/literature", label: "文献" },
  { href: "/rag", label: "问答" },
  { href: "/network", label: "网药" },
  { href: "/evals/rag-ad", label: "评估" },
  { href: "/compliance", label: "合规" },
];

const taskCards: Array<{
  href: string;
  icon: ReactNode;
  eyebrow: string;
  title: string;
  body: string;
  metric: string;
}> = [
  {
    href: "/literature",
    icon: <FileSearchOutlined aria-hidden="true" />,
    eyebrow: "Evidence intake",
    title: "文献检索",
    body: "先核对来源、年份、摘要与 PDF 状态，再进入证据摘录和人工校正。",
    metric: "Seed / PubMed / PDF",
  },
  {
    href: "/rag",
    icon: <QuestionCircleOutlined aria-hidden="true" />,
    eyebrow: "Citation QA",
    title: "RAG 问答",
    body: "围绕 AD 问题返回可追溯答案，显式展示检索边界与 citation cards。",
    metric: "Answer + grounding",
  },
  {
    href: "/network",
    icon: <BranchesOutlined aria-hidden="true" />,
    eyebrow: "Mechanism map",
    title: "网络药理学",
    body: "保留成分、靶点、通路、疾病概念边界，当前验证 mock 任务链路。",
    metric: "Compound / target",
  },
  {
    href: "/evals/rag-ad",
    icon: <ExperimentOutlined aria-hidden="true" />,
    eyebrow: "Regression",
    title: "RAG 评估",
    body: "用 50 题评估集检查引用命中、chunk 命中、免责声明覆盖与禁用语。",
    metric: "50 questions",
  },
];

const controlRows = [
  { label: "Scope", value: "特应性皮炎", note: "AD only" },
  { label: "Audience", value: "医生 / 科研人员", note: "非 C 端" },
  { label: "Inference", value: "Deterministic retrieval", note: "本地链路" },
  { label: "Heavy deps", value: "暂不接真实 LLM / embedding", note: "MVP-A" },
];

function PrimaryLink({
  href,
  children,
  variant = "solid",
}: Readonly<{ href: string; children: ReactNode; variant?: "solid" | "outline" }>) {
  return (
    <a className={`home-action home-action-${variant}`} href={href}>
      <span>{children}</span>
      <ArrowRightOutlined aria-hidden="true" />
    </a>
  );
}

function TaskCard({
  card,
}: Readonly<{
  card: (typeof taskCards)[number];
}>) {
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
    <main className="workbench-page home-page" style={{ minHeight: "100vh", padding: "clamp(20px, 4vw, 48px)" }}>
      <section className="workbench-frame">
        <header className="home-topbar">
          <a className="home-brand" href="/" aria-label="Qiyan Nexus 首页">
            <span className="home-brand-mark">
              <AuditOutlined aria-hidden="true" />
            </span>
            <span className="home-brand-copy">
              <span className="home-brand-title">Qiyan Nexus</span>
              <span className="home-brand-subtitle">AD Evidence Workbench</span>
            </span>
          </a>

          <nav className="workbench-nav" aria-label="工作台导航">
            {navItems.map((item) => (
              <a key={item.href} href={item.href}>
                {item.label}
              </a>
            ))}
          </nav>
        </header>

        <article className="home-hero" aria-label="Qiyan Nexus 首页">
          <div className="home-hero-main">
            <p className="workbench-kicker">Clinical evidence operating layer</p>
            <h1 className="home-title">把特应性皮炎证据变成可审计的科研路径</h1>
            <p className="home-summary">
              面向医生与科研人员的中医药证据工作台。文献、问答、网络药理学和评估回归被放在同一条审阅链路里，先确认来源，再判断结论边界。
            </p>
            <div className="home-actions">
              <PrimaryLink href="/literature">进入证据检索</PrimaryLink>
              <PrimaryLink href="/rag" variant="outline">
                查看引用问答
              </PrimaryLink>
            </div>
          </div>

          <aside className="home-boundary-panel" aria-label="当前产品边界摘要">
            <div>
              <span>MVP-A</span>
              <strong>证据工作台收尾完成</strong>
            </div>
            <div>
              <span>RAG eval</span>
              <strong>50 题 seed benchmark</strong>
            </div>
            <div>
              <span>Default</span>
              <strong>本地 deterministic retrieval</strong>
            </div>
          </aside>
        </article>

        <section className="workbench-content-band" aria-label="工作台任务入口">
          <div className="home-section-head">
            <div>
              <p className="workbench-kicker">Workbench routes</p>
              <h2>每个入口都对应一段可复核的科研动作</h2>
            </div>
            <p>
              首页展示当前能力、数据边界和审阅顺序，让使用者先理解证据来源，再进入具体工具。
            </p>
          </div>

          <div className="task-grid">
            {taskCards.map((card) => (
              <TaskCard key={card.href} card={card} />
            ))}
          </div>

          <section className="home-control-panel" aria-label="产品边界">
            <div className="home-control-intro">
              <SafetyCertificateOutlined aria-hidden="true" />
              <div>
                <h2>边界可见，结论才可信</h2>
                <p>
                  当前版本只做证据整理、链路验证和能力回归，不替代诊断、处方或个体治疗判断。
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
      </section>
    </main>
  );
}
