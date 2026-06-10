import type { Metadata } from "next";
import "./globals.css";
import { ErrorBoundary } from "../components/ErrorBoundary";

export const metadata: Metadata = {
  title: "Qiyan Nexus",
  description: "面向特应性皮炎的中医药证据与科研工作台",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>
        <ErrorBoundary>{children}</ErrorBoundary>
      </body>
    </html>
  );
}
