import { notFound } from "next/navigation";

import { CardBodyText, CardMetaRow } from "../../../components/CardMeta";
import DemoDataBanner from "../../../components/DemoDataBanner";
import EntityChips from "../../../components/EntityChips";
import LiteraturePdfUploadClient from "../../../components/LiteraturePdfUploadClient";
import { getLiteratureDetail, getLiteratureSourceLabel } from "../../../lib/api/literature";
import { getComplianceNavigationLinks } from "../../../lib/compliance-page";

type LiteratureDetailPageProps = {
  params: Promise<{
    id: string;
  }>;
};

export default async function LiteratureDetailPage({ params }: LiteratureDetailPageProps) {
  const { id } = await params;

  try {
    const item = await getLiteratureDetail(id);
    const navigationLinks = getComplianceNavigationLinks();

    return (
      <main className="workbench-page" style={{ minHeight: "100vh", padding: "clamp(20px, 4vw, 48px)" }}>
        <section className="workbench-frame workbench-frame-narrow">
          <nav aria-label="工作台导航" className="workbench-nav">
            {navigationLinks.map((link) => {
              const isCurrent = link.href === "/literature";

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
              <h1 className="workbench-title workbench-detail-title">文献详情</h1>
              <p className="workbench-summary">
                先核对文献来源、摘要与年份，再进入 PDF 上传、解析状态与后续人工校正流程。
              </p>
            </div>
            <aside className="workbench-hero-aside" aria-label="文献详情元数据">
              <div className="workbench-stat">
                <span>Language</span>
                <strong>{item.language === "zh" ? "中文" : "英文"}</strong>
              </div>
              <div className="workbench-stat">
                <span>Source</span>
                <strong>{getLiteratureSourceLabel(item.source_type)}</strong>
              </div>
              <div className="workbench-stat">
                <span>Year</span>
                <strong>{String(item.year)}</strong>
              </div>
            </aside>
          </article>

          <div className="workbench-content-band">
            <DemoDataBanner compact />

            <article>
              <CardMetaRow
                items={[
                  `语言 ${item.language === "zh" ? "中文" : "英文"}`,
                  `来源 ${getLiteratureSourceLabel(item.source_type)}`,
                  `期刊 ${item.source}`,
                  `年份 ${String(item.year)}`,
                  `文献 ID ${item.id}`,
                ]}
              />
              <EntityChips
                ids={item.related_entity_ids ?? []}
                emptyHint="该文献尚未挂载网药实体；如需跳转 /network 请使用相关词查询。"
              />
              <h2 style={{ color: "#10231f", fontSize: 34, lineHeight: 1.28, margin: "18px 0 14px" }}>{item.title}</h2>
              <div style={{ display: "grid", gap: 12, color: "#334155", fontSize: 17, lineHeight: 1.7 }}>
                <CardBodyText>{item.snippet}</CardBodyText>
              </div>
            </article>

            <LiteraturePdfUploadClient item={item} />
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
  } catch {
    notFound();
  }
}
