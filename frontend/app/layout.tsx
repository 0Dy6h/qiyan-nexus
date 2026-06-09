import type { Metadata } from "next";
import "antd/dist/reset.css";
import "./workbench.css";
import WorkbenchShell from "../components/WorkbenchShell";

export const metadata: Metadata = {
  title: "Qiyan Nexus",
  description: "面向特应性皮炎的中医药证据与科研工作台",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>
        <WorkbenchShell>{children}</WorkbenchShell>
      </body>
    </html>
  );
}
