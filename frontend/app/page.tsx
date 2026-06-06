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

const signalCards = [
  { value: "Seed / PubMed", label: "文献证据信号" },
  { value: "50", label: "AD RAG 评估问题" },
  { value: "PDF pending", label: "上传解析状态追踪" },
  { value: "Mock graph", label: "成分-靶点-通路链" },
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
              <h1 className="home-title">你好，告诉我们你想核对的证据问题</h1>
              <p className="home-summary">
                捕捉 AD 文献、上传 PDF、RAG 引用与网药 mock 信号，把研究问题送入可追溯、可评估、可声明边界的证据工作台。
              </p>
              <div className="home-app-console">
                <div className="home-mode-tabs" role="tablist" aria-label="研究工作模式">
                  <span className="home-mode-tab home-mode-tab-active" role="tab" aria-selected="true">
                    <QuestionCircleOutlined aria-hidden="true" />
                    RAG 引用问答
                  </span>
                  <span className="home-mode-tab" role="tab" aria-selected="false">
                    <BranchesOutlined aria-hidden="true" />
                    网药机制链
                  </span>
                </div>

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
                      <a href="/network" aria-label="进入网络药理学">
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
    </>
  );
}
