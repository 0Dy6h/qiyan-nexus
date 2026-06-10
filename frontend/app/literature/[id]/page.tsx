import { notFound } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
      <main className="min-h-screen bg-gray-50 px-5 md:px-8 lg:px-12 py-8">
        <section className="max-w-4xl mx-auto grid gap-5">
          <nav aria-label="工作台导航" className="flex gap-3 flex-wrap">
            {navigationLinks.map((link) => {
              const isCurrent = link.href === "/literature";
              return (
                <Button
                  key={link.href}
                  asChild
                  variant={isCurrent ? "default" : "outline"}
                  size="sm"
                  className={isCurrent ? "bg-primary-600 hover:bg-primary-700" : ""}
                >
                  <a href={link.href} aria-current={isCurrent ? "page" : undefined}>
                    {link.label}
                  </a>
                </Button>
              );
            })}
          </nav>

          <DemoDataBanner compact />

          <Card>
            <CardContent className="pt-6 grid gap-4">
              <div className="grid gap-2">
                <p className="text-primary-600 font-bold text-sm">Evidence workbench</p>
                <h2 className="text-gray-900 text-2xl font-semibold">文献详情</h2>
                <p className="text-gray-600 text-sm leading-relaxed">
                  先核对文献来源、摘要与年份，再进入 PDF 上传、解析状态与后续人工校正流程。
                </p>
              </div>

              <div className="flex gap-2 flex-wrap">
                <Badge variant="secondary" className="text-xs">
                  语言 {item.language === "zh" ? "中文" : "英文"}
                </Badge>
                <Badge variant="outline" className="text-xs">
                  来源 {getLiteratureSourceLabel(item.source_type)}
                </Badge>
                <Badge variant="outline" className="text-xs">
                  期刊 {item.source}
                </Badge>
                <Badge variant="outline" className="text-xs">
                  年份 {String(item.year)}
                </Badge>
                <Badge variant="outline" className="text-xs">
                  文献 ID {item.id}
                </Badge>
              </div>

              <EntityChips
                ids={item.related_entity_ids ?? []}
                emptyHint="该文献尚未挂载网药实体；如需跳转 /network 请使用相关词查询。"
              />

              <h1 className="text-gray-900 text-4xl font-semibold leading-tight">{item.title}</h1>

              <div className="text-gray-700 text-base leading-relaxed">
                <p>{item.snippet}</p>
              </div>
            </CardContent>
          </Card>

          <LiteraturePdfUploadClient item={item} />

          <Card className="bg-gray-50 border-gray-200">
            <CardContent className="pt-5 grid gap-1.5">
              <p className="text-gray-700 text-sm font-semibold">使用提醒</p>
              <p className="text-gray-600 text-sm leading-relaxed">
                本页面信息仅用于研究与产品能力说明，不构成诊断或治疗建议；实际判断仍需结合临床指南、原始文献与专业医生意见。
              </p>
            </CardContent>
          </Card>
        </section>
      </main>
    );
  } catch {
    notFound();
  }
}
