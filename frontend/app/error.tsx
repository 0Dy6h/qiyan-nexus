"use client";

import { useEffect } from "react";

/**
 * App Router error boundary (route-level).
 *
 * Next.js automatically wraps route segments with this error UI.
 * Catches errors in the page and its children during rendering.
 */
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log error to console; in production this could go to a logging service
    console.error("Route error:", error);
  }, [error]);

  return (
    <div
      style={{
        padding: "clamp(20px, 4vw, 48px)",
        maxWidth: 800,
        margin: "0 auto",
      }}
    >
      <div
        style={{
          backgroundColor: "#fef2f2",
          border: "1px solid #fecaca",
          borderRadius: 8,
          padding: 24,
        }}
      >
        <h2
          style={{
            color: "#991b1b",
            fontSize: 20,
            fontWeight: 700,
            margin: "0 0 12px",
          }}
        >
          页面加载出错
        </h2>
        <p
          style={{
            color: "#7f1d1d",
            lineHeight: 1.6,
            margin: "0 0 16px",
          }}
        >
          抱歉，页面遇到了意外错误。请尝试重试，或返回首页。
        </p>
        {error.digest && (
          <p
            style={{
              color: "#7f1d1d",
              fontSize: 13,
              fontFamily: "monospace",
              margin: "0 0 16px",
            }}
          >
            错误标识：{error.digest}
          </p>
        )}
        <div style={{ marginTop: 20 }}>
          <button
            onClick={reset}
            style={{
              padding: "8px 16px",
              backgroundColor: "#dc2626",
              color: "#ffffff",
              border: "none",
              borderRadius: 6,
              fontSize: 14,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            重试
          </button>
          <a
            href="/"
            style={{
              marginLeft: 12,
              padding: "8px 16px",
              color: "#991b1b",
              fontSize: 14,
              fontWeight: 600,
              textDecoration: "none",
            }}
          >
            返回首页
          </a>
        </div>
      </div>
    </div>
  );
}
