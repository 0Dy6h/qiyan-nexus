"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  AuditOutlined,
  GlobalOutlined,
  PlusOutlined,
  UserOutlined,
} from "@ant-design/icons";

const navItems = [
  { href: "/literature", label: "文献检索" },
  { href: "/rag", label: "RAG 问答" },
  { href: "/network", label: "机制线索" },
  { href: "/evals/rag-ad", label: "RAG 评估" },
  { href: "/compliance", label: "合规边界" },
];

const railSignals = [
  { title: "PubMed runtime", time: "实时同步入口" },
  { title: "PDF parse status", time: "上传后追踪" },
];

function getCurrentNavHref(pathname: string) {
  if (pathname.startsWith("/literature")) {
    return "/literature";
  }

  if (pathname.startsWith("/evals/rag-ad")) {
    return "/evals/rag-ad";
  }

  return navItems.find((item) => pathname === item.href || pathname.startsWith(`${item.href}/`))?.href;
}

export default function WorkbenchShell({ children }: Readonly<{ children: ReactNode }>) {
  const pathname = usePathname() ?? "/";
  const isHome = pathname === "/";
  const currentHref = getCurrentNavHref(pathname);

  return (
    <main className={`workbench-page${isHome ? " home-page" : ""}`} style={{ minHeight: "100vh", padding: "clamp(12px, 2vw, 24px)" }}>
      <div className="meteor-shower" aria-hidden="true">
        <div className="meteor"></div>
        <div className="meteor teal"></div>
        <div className="meteor"></div>
        <div className="meteor purple"></div>
        <div className="meteor"></div>
        <div className="meteor teal"></div>
        <div className="meteor"></div>
        <div className="meteor"></div>
      </div>

      <section className="workbench-frame home-app-frame">
        <aside className="home-app-rail" aria-label="工作台侧栏">
          <Link className="home-brand" href="/" aria-label="Qiyan Nexus 首页" aria-current={isHome ? "page" : undefined}>
            <span className="home-brand-mark">
              <AuditOutlined aria-hidden="true" />
            </span>
            <span className="home-brand-copy">
              <span className="home-brand-title">Qiyan Nexus</span>
              <span className="home-brand-subtitle">AD Evidence Workbench</span>
            </span>
          </Link>

          <Link className="home-new-session" href="/rag">
            <PlusOutlined aria-hidden="true" />
            <span>开启证据问答</span>
          </Link>

          <nav className="workbench-nav" aria-label="工作台导航">
            {navItems.map((item) => (
              <Link key={item.href} href={item.href} aria-current={currentHref === item.href ? "page" : undefined}>
                {item.label}
              </Link>
            ))}
          </nav>

          <section className="home-rail-signal" aria-label="证据信号摘要">
            <div className="home-rail-signal-head">
              <GlobalOutlined aria-hidden="true" />
              <span>证据信号</span>
              <strong>全部</strong>
            </div>
            {railSignals.map((signal) => (
              <Link className="home-rail-signal-item" href="/literature" key={signal.title}>
                <span>{signal.title}</span>
                <small>{signal.time}</small>
              </Link>
            ))}
          </section>

          <div className="home-account-entry" aria-label="账户登录入口预留">
            <UserOutlined aria-hidden="true" />
            <span>
              <strong>登录 / 注册</strong>
              <small>预留账户入口</small>
            </span>
          </div>
        </aside>

        <div className={isHome ? "home-main-stack" : "workbench-main-stack"}>{children}</div>
      </section>
    </main>
  );
}
