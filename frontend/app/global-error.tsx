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
            padding: "clamp(12px, 2vw, 24px)",
            maxWidth: 800,
            margin: "0 auto",
            fontFamily: "system-ui, sans-serif",
            minHeight: "100vh",
            backgroundColor: "#020508",
            color: "#f6fbff",
          }}
        >
          <div
            style={{
              backgroundColor: "#2a0d14",
              border: "1px solid #fb7185",
              borderRadius: 20,
              padding: 24,
            }}
          >
            <h2
              style={{
                color: "#fecdd3",
                fontSize: 20,
                fontWeight: 700,
                margin: "0 0 12px",
              }}
            >
              应用加载出错
            </h2>
            <p
              style={{
                color: "#ffe4e6",
                lineHeight: 1.6,
                margin: "0 0 16px",
              }}
            >
              抱歉，应用遇到了严重错误。请尝试重新加载。
            </p>
            {error.digest && (
              <p
                style={{
                  color: "#ffe4e6",
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
                backgroundColor: "#e11d48",
                color: "#ffffff",
                border: "none",
                borderRadius: 12,
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
