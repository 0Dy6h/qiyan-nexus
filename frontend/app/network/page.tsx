import { Suspense } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import NetworkAnalysisClient from "../../components/NetworkAnalysisClient";
import StatusPanel from "../../components/StatusPanel";
import { getComplianceNavigationLinks } from "../../lib/compliance-page";

export default function NetworkPage() {
  const navigationLinks = getComplianceNavigationLinks();

  return (
    <main className="min-h-screen bg-gray-50 px-5 md:px-8 lg:px-12 py-8">
      <section className="max-w-5xl mx-auto grid gap-5">
        <nav aria-label="工作台导航" className="flex gap-3 flex-wrap">
          {navigationLinks.map((link) => {
            const isCurrent = link.href === "/network";
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

        <Card>
          <CardContent className="pt-6 grid gap-2">
            <p className="text-primary-600 font-bold text-sm">Evidence workbench</p>
            <h1 className="text-gray-900 text-4xl font-semibold">网络药理学（mock）</h1>
            <p className="text-gray-600 text-base leading-relaxed">
              当前页面调用后端 <code className="bg-gray-100 px-1 rounded text-sm">/api/network/analyze</code> 与 <code className="bg-gray-100 px-1 rounded text-sm">/api/network/result</code>，用于验证「成分-靶点-通路-疾病」链路与异步任务壳的第一条前后端链路。
            </p>
          </CardContent>
        </Card>

        <Suspense fallback={<StatusPanel message="加载网药分析面板..." />}>
          <NetworkAnalysisClient />
        </Suspense>

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
}
