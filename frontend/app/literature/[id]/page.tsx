import { notFound } from "next/navigation";

import { CardBodyText, CardMetaRow } from "../../../components/CardMeta";
import LiteraturePdfUploadClient from "../../../components/LiteraturePdfUploadClient";
import { getLiteratureDetail, getLiteratureSourceLabel } from "../../../lib/api/literature";
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

    return (
      <main style={{ minHeight: "100vh", background: "#f8fafc", padding: 48 }}>
        <section style={{ maxWidth: 960, margin: "0 auto", display: "grid", gap: 20 }}>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
            <a href="/rag" style={{ color: "#0d9488", fontWeight: 700 }}>
              ← 返回 RAG 问答
            </a>
            <a href="/literature" style={{ color: "#0d9488", fontWeight: 700 }}>
              返回文献检索
            </a>
          </div>

          <article style={getSurfaceSectionStyle()}>
            <div style={{ display: "grid", gap: 8, marginBottom: 16 }}>
              <h2 style={{ color: "#1e293b", fontSize: 24, margin: 0 }}>文献详情</h2>
              <p style={{ color: "#64748b", margin: 0, lineHeight: 1.6 }}>
                先核对文献来源与摘要，再进入 PDF 上传、解析状态与后续人工补录流程。
              </p>
            </div>
            <CardMetaRow
              items={[
                item.language === "zh" ? "中文" : "英文",
                getLiteratureSourceLabel(item.source_type),
                item.source,
                String(item.year),
                `文献 ID ${item.id}`,
              ]}
            />
            <h1 style={{ color: "#1e293b", fontSize: 36, lineHeight: 1.3 }}>{item.title}</h1>
            <div style={{ display: "grid", gap: 12, color: "#334155", fontSize: 17, lineHeight: 1.7 }}>
              <CardBodyText>{item.snippet}</CardBodyText>
            </div>
          </article>

          <LiteraturePdfUploadClient item={item} />

          <p style={{ color: "#64748b", margin: 0 }}>非诊断结论、需结合临床。</p>
        </section>
      </main>
    );
  } catch {
    notFound();
  }
}
