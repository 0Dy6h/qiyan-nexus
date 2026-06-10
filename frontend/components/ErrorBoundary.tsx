"use client";

import React from "react";

type ErrorBoundaryProps = {
  children: React.ReactNode;
  fallback?: (error: Error, reset: () => void) => React.ReactNode;
};

type ErrorBoundaryState = {
  hasError: boolean;
  error: Error | null;
};

/**
 * React Error Boundary component for graceful error handling.
 * Catches JavaScript errors in child component tree and displays fallback UI.
 */
export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log error to console in development
    if (process.env.NODE_ENV === "development") {
      console.error("ErrorBoundary caught an error:", error, errorInfo);
    }
    // TODO: Send to error tracking service in production (e.g., Sentry)
  }

  reset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError && this.state.error) {
      if (this.props.fallback) {
        return this.props.fallback(this.state.error, this.reset);
      }

      // Default fallback UI
      return (
        <div className="flex min-h-[400px] flex-col items-center justify-center gap-4 p-8">
          <div className="text-center">
            <h2 className="mb-2 text-xl font-semibold text-gray-900">出错了</h2>
            <p className="mb-4 text-sm text-gray-600">
              页面遇到了意外错误。请尝试刷新页面或联系支持。
            </p>
            {process.env.NODE_ENV === "development" && (
              <details className="mt-4 rounded border border-gray-200 bg-gray-50 p-4 text-left text-xs">
                <summary className="cursor-pointer font-medium text-gray-700">错误详情</summary>
                <pre className="mt-2 whitespace-pre-wrap text-red-600">
                  {this.state.error.message}
                  {"\n\n"}
                  {this.state.error.stack}
                </pre>
              </details>
            )}
          </div>
          <button
            onClick={this.reset}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            重试
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
