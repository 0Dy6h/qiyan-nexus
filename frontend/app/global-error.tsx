"use client";

/**
 * Global error boundary (root-level).
 *
 * Catches errors in the root layout. This replaces the entire page,
 * including the <html> and <body> tags, so it must render them itself.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="zh-CN">
      <body>
        <div
          style={{
            padding: "clamp(20px, 4vw, 48px)",
            maxWidth: 800,
            margin: "0 auto",
            fontFamily: "system-ui, sans-serif",
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
              应用加载出错
            </h2>
            <p
              style={{
                color: "#7f1d1d",
                lineHeight: 1.6,
                margin: "0 0 16px",
              }}
            >
              抱歉，应用遇到了严重错误。请尝试重新加载。
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
                marginTop: 8,
              }}
            >
              重新加载
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
