import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-gray-50 px-5 md:px-8 lg:px-12 py-12">
      <Card className="max-w-4xl mx-auto">
        <CardContent className="pt-10 grid gap-6">
          <div className="grid gap-3">
            <p className="text-primary-600 font-bold text-sm">Qiyan Nexus · AD 专病科研工作台</p>
            <h1 className="text-gray-900 text-5xl font-semibold leading-tight">
              面向特应性皮炎的中医药证据与科研工作台
            </h1>
            <p className="text-gray-600 text-lg leading-relaxed">
              面向医生与科研人员，围绕特应性皮炎提供文献检索、RAG 问答、网络药理学分析与知识图谱能力。
            </p>
            <p className="text-gray-500 text-sm">非诊断结论、需结合临床。</p>
          </div>

          <div className="flex gap-3 flex-wrap">
            <Button asChild className="bg-primary-600 hover:bg-primary-700">
              <a href="/literature">进入文献检索</a>
            </Button>
            <Button asChild variant="outline">
              <a href="/rag">进入 RAG 问答</a>
            </Button>
            <Button asChild variant="outline">
              <a href="/network">进入网络药理学</a>
            </Button>
            <Button asChild variant="secondary">
              <a href="/compliance">查看合规说明</a>
            </Button>
            <Button asChild variant="secondary">
              <a href="/evals/rag-ad">运行 RAG 评估</a>
            </Button>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
