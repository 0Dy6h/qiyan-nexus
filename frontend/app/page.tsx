import type { ReactNode } from "react";
import {
  ArrowRightOutlined,
  BranchesOutlined,
  ExperimentOutlined,
  FileSearchOutlined,
  PaperClipOutlined,
  PictureOutlined,
  QuestionCircleOutlined,
  SafetyCertificateOutlined,
  SendOutlined,
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
    href: "/literature",
    icon: <FileSearchOutlined aria-hidden="true" />,
    eyebrow: "Step 1",
    title: "查证据",
    body: "检索 AD 中医药文献，核对演示样本、PubMed 实时同步与用户上传 PDF 的来源边界。",
    metric: "文献 / PDF / 来源",
  },
  {
    href: "/rag",
    icon: <QuestionCircleOutlined aria-hidden="true" />,
    eyebrow: "Step 2",
    title: "问证据",
    body: "围绕真实研究问题生成证据简报，默认先看答案、免责声明与引用卡片，再展开技术审计。",
    metric: "答案 / 引用 / 导出",
  },
  {
    href: "/network",
    icon: <BranchesOutlined aria-hidden="true" />,
    eyebrow: "Step 3",
    title: "看机制线索",
    body: "查看方药-成分-靶点-通路链条，默认作为探索性机制线索，不作为正式网络药理学结论。",
    metric: "Mock / opt-in live",
  },
  {
    href: "/evals/rag-ad",
    icon: <ExperimentOutlined aria-hidden="true" />,
    eyebrow: "Audit",
    title: "回归评估",
    body: "用 50 题评估集检查引用命中、chunk 命中、免责声明覆盖与禁用语，供内部收口使用。",
    metric: "50 questions",
  },
];

const controlRows = [
  { label: "Scope", value: "特应性皮炎", note: "AD only" },
  { label: "Audience", value: "医生 / 科研人员", note: "非 C 端" },
  { label: "Inference", value: "Deterministic retrieval", note: "本地链路" },
  { label: "Heavy deps", value: "暂不接真实 LLM / embedding", note: "MVP-A" },
];

const signalCards = [
  { value: "查文献", label: "定位 AD 中医药证据" },
  { value: "50", label: "AD RAG 评估问题" },
  { value: "上传/归档证据", label: "PDF 解析状态追踪" },
  { value: "提问 / 核引用 / 导出", label: "可导出的证据材料" },
  { value: DISCLAIMER, label: "输出边界" },
];

const promptSuggestions = [
  "特应性皮炎和肠-脑-皮肤轴有什么关系？",
  "消风散可能涉及哪些靶点？",
  "上传 PDF 证据如何进入引用卡片？",
  "RAG 评估如何检查免责声明覆盖？",
];

function buildRagQuestionHref(question: string) {
  return `/rag?question=${encodeURIComponent(question)}`;
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
    <>
          <article className="home-hero" aria-label="Qiyan Nexus 首页">
            <div className="home-hero-main">
              <p className="workbench-kicker">Clinical evidence operating layer</p>
              <h1 className="home-title">AD 中医药证据工作台</h1>
              <p className="home-summary">
                从查文献、上传/归档证据，到提问、核引用、导出可导出的证据材料；先完成一条可追溯的核心工作流，再进入机制线索探索。
              </p>
              <div className="home-app-console">
                <nav className="home-mode-tabs" aria-label="研究工作模式">
                  <a className="home-mode-tab home-mode-tab-active" href="/rag">
                    <QuestionCircleOutlined aria-hidden="true" />
                    问证据
                  </a>
                  <a className="home-mode-tab" href="/network">
                    <BranchesOutlined aria-hidden="true" />
                    看机制线索
                  </a>
                </nav>

                <form className="home-prompt-card" action="/rag" method="get">
                  <textarea
                    name="question"
                    aria-label="输入证据问题"
                    defaultValue={promptSuggestions[0]}
                  />
                  <div className="home-prompt-tools">
                    <span className="home-tool-icons" aria-label="工作台快捷入口">
                      <a href="/literature" aria-label="进入文献检索">
                        <PaperClipOutlined aria-hidden="true" />
                      </a>
                      <a href="/network" aria-label="进入机制线索探索">
                        <PictureOutlined aria-hidden="true" />
                      </a>
                    </span>
                    <button className="home-send-button" type="submit" aria-label="发送到 RAG 问答">
                      <SendOutlined aria-hidden="true" />
                    </button>
                  </div>
                </form>

                <div className="home-suggestion-row" aria-label="试试这些问题">
                  <span className="home-suggestion-label">试试问这些</span>
                  {promptSuggestions.slice(1).map((question) => (
                    <a className="home-suggestion-chip" href={buildRagQuestionHref(question)} key={question}>
                      {question}
                      <ArrowRightOutlined aria-hidden="true" />
                    </a>
                  ))}
                </div>
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

          <section className="home-signal-strip" aria-label="证据信号概览">
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
                <p className="workbench-kicker">Core workflow</p>
                <h2>先完成核心证据整理，再评价更多模块</h2>
              </div>
              <p>
                首页只强调真实 reviewer 需要走通的主路径：查文献 → 上传/归档证据 → 提问 → 核引用 → 导出；其余能力作为审计或后续探索入口。
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
    </>
  );
}
