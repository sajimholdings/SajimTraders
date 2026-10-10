"use client";

import React from "react";
import { trackAction } from "../lib/logger";

interface ErrorBoundaryProps {
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

/** Catches render errors anywhere in the app and shows a recoverable fallback. */
export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error) {
    trackAction("CLIENT_RENDER_ERROR", { message: error.message });
  }

  private handleReload = () => {
    this.setState({ hasError: false });
    if (typeof window !== "undefined") window.location.reload();
  };

  render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center p-6">
        <div className="max-w-sm w-full bg-[#111111] border border-red-500/30 rounded-2xl p-6 text-center">
          <h1 className="text-base font-bold mb-2">Something went wrong</h1>
          <p className="text-xs text-gray-400 mb-4">
            The cockpit hit an unexpected error. Your account and open trades are not affected.
          </p>
          <button
            type="button"
            onClick={this.handleReload}
            className="w-full py-2.5 rounded-xl bg-green-500 text-black text-xs font-bold hover:bg-green-400"
          >
            Reload
          </button>
        </div>
      </div>
    );
  }
}
