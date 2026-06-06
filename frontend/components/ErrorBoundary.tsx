"use client";

import { Component, ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * Error Boundary component to catch React rendering errors.
 *
 * Wraps child components and displays a fallback UI when an error occurs.
 * Prevents the entire app from crashing due to a single component error.
 */
export default class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    // Update state so the next render will show the fallback UI
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: { componentStack: string }): void {
    // Log error to console in development
    console.error("ErrorBoundary caught an error:", error, errorInfo);

    // In production, you could send error to logging service
    // Example: logErrorToService(error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default fallback UI
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
              抱歉，页面遇到了意外错误。请尝试刷新页面，或稍后重试。
            </p>
            {this.state.error && (
              <details style={{ marginTop: 16 }}>
                <summary
                  style={{
                    color: "#991b1b",
                    fontSize: 14,
                    cursor: "pointer",
                    fontWeight: 600,
                  }}
                >
                  错误详情
                </summary>
                <pre
                  style={{
                    marginTop: 12,
                    padding: 12,
                    backgroundColor: "#ffffff",
                    border: "1px solid #fecaca",
                    borderRadius: 4,
                    fontSize: 13,
                    overflow: "auto",
                    color: "#7f1d1d",
                  }}
                >
                  {this.state.error.toString()}
                </pre>
              </details>
            )}
            <div style={{ marginTop: 20 }}>
              <button
                onClick={() => window.location.reload()}
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
                刷新页面
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

    return this.props.children;
  }
}
