import { notFound } from "next/navigation";

import { CardBodyText, CardMetaRow } from "../../../components/CardMeta";
import DemoDataBanner from "../../../components/DemoDataBanner";
import LiteraturePdfUploadClient from "../../../components/LiteraturePdfUploadClient";
import { getLiteratureDetail, getLiteratureSourceLabel } from "../../../lib/api/literature";
import { getComplianceNavigationLinks } from "../../../lib/compliance-page";
import { getSurfaceSectionStyle } from "../../../lib/ui/surfaces";

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
      <main style={{ minHeight: "100vh", background: "#f8fafc", padding: "clamp(20px, 4vw, 48px)" }}>
        <section style={{ maxWidth: 960, margin: "0 auto", display: "grid", gap: 20 }}>
          <nav aria-label="工作台导航" style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {navigationLinks.map((link) => {
              const isCurrent = link.href === "/literature";

              return (
                <a
                  key={link.href}
                  href={link.href}
                  aria-current={isCurrent ? "page" : undefined}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    borderRadius: 999,
                    background: isCurrent ? "#ecfeff" : "transparent",
                    border: `1px solid ${isCurrent ? "#99f6e4" : "#cbd5e1"}`,
                    color: isCurrent ? "#115e59" : "#475569",
                    fontSize: 14,
                    fontWeight: isCurrent ? 700 : 600,
                    padding: "10px 14px",
                    textDecoration: "none",
                    minHeight: 44,
                  }}
                >
                  {link.label}
                </a>
              );
            })}
          </nav>

          <DemoDataBanner compact />

          <article style={getSurfaceSectionStyle()}>
            <div style={{ display: "grid", gap: 8, marginBottom: 16 }}>
              <p style={{ color: "#0d9488", fontWeight: 700, margin: 0 }}>Evidence workbench</p>
              <h2 style={{ color: "#1e293b", fontSize: 24, margin: 0 }}>文献详情</h2>
              <p style={{ color: "#64748b", margin: 0, lineHeight: 1.6 }}>
                先核对文献来源、摘要与年份，再进入 PDF 上传、解析状态与后续人工校正流程。
              </p>
            </div>
            <CardMetaRow
              items={[
                `语言 ${item.language === "zh" ? "中文" : "英文"}`,
                `来源 ${getLiteratureSourceLabel(item.source_type)}`,
                `期刊 ${item.source}`,
                `年份 ${String(item.year)}`,
                `文献 ID ${item.id}`,
              ]}
            />
            <h1 style={{ color: "#1e293b", fontSize: 36, lineHeight: 1.3 }}>{item.title}</h1>
            <div style={{ display: "grid", gap: 12, color: "#334155", fontSize: 17, lineHeight: 1.7 }}>
              <CardBodyText>{item.snippet}</CardBodyText>
            </div>
          </article>

          <LiteraturePdfUploadClient item={item} />

          <section
            aria-label="使用提醒"
            style={{
              ...getSurfaceSectionStyle(),
              background: "#f8fafc",
              border: "1px solid #e2e8f0",
              padding: 20,
            }}
          >
            <div style={{ display: "grid", gap: 6 }}>
              <p style={{ color: "#334155", fontSize: 14, fontWeight: 700, margin: 0 }}>使用提醒</p>
              <p style={{ color: "#64748b", fontSize: 14, lineHeight: 1.7, margin: 0 }}>
                本页面信息仅用于研究与产品能力说明，不构成诊断或治疗建议；实际判断仍需结合临床指南、原始文献与专业医生意见。
              </p>
            </div>
          </section>
        </section>
      </main>
    );
  } catch {
    notFound();
  }
}
