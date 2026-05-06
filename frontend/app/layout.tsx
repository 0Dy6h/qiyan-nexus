import type { Metadata } from "next";
import "antd/dist/reset.css";

export const metadata: Metadata = {
  title: "Tcm Tech",
  description: "中医药精准诊疗与科研一体化平台",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
