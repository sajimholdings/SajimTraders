"use client";

import React, { useState } from "react";
import { X, Lock, Mail, User, ArrowRight, ShieldCheck } from "lucide-react";
import { supabase } from "../lib/supabase";
import { trackAction } from "../lib/logger";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (userData: { email: string; fullName: string; id: string }) => void;
  initialMode?: "signup" | "signin";
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  initialMode = "signup",
}) => {
  const [mode, setMode] = useState<"signup" | "signin">(initialMode);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setLoading(true);

    if (password.length < 6) {
      setErrorMsg("Password must be at least 6 characters long.");
      setLoading(false);
      return;
    }

    if (mode === "signup") {
      trackAction("AUTH_SIGNUP_ATTEMPT", { email });
      const res = await supabase.signUp(email, password, fullName);

      if (res.error) {
        setErrorMsg(res.error);
        setLoading(false);
        trackAction("AUTH_SIGNUP_ERROR", { error: res.error });
        return;
      }

      // Automatically sign in to obtain access token
      const loginRes = await supabase.signInWithPassword(email, password);
      setLoading(false);

      const resolvedName = fullName.trim() || email.split("@")[0];
      const userId = res.user?.id || loginRes.user?.id || "USER-" + Math.floor(Math.random() * 10000);

      trackAction("AUTH_SIGNUP_SUCCESS", { email, id: userId });
      onSuccess({ email, fullName: resolvedName, id: userId });
      onClose();
    } else {
      // Sign In mode
      trackAction("AUTH_SIGNIN_ATTEMPT", { email });
      const res = await supabase.signInWithPassword(email, password);
      setLoading(false);

      if (res.error) {
        setErrorMsg(res.error);
        trackAction("AUTH_SIGNIN_ERROR", { error: res.error });
        return;
      }

      const user = res.user;
      const resolvedName = user?.user_metadata?.full_name || email.split("@")[0] || "Trader";
      const userId = user?.id || "USER-" + Math.floor(Math.random() * 10000);

      trackAction("AUTH_SIGNIN_SUCCESS", { email, id: userId });
      onSuccess({ email, fullName: resolvedName, id: userId });
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4 animate-fadeUp"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-sm bg-[#111111] border border-white/[0.08] rounded-3xl p-6 shadow-2xl relative text-white">
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-green-500/10 border border-green-500/20 flex items-center justify-center text-green-400">
              <Lock className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-sm text-white leading-tight">
                {mode === "signup" ? "Create Trader Account" : "Welcome Back"}
              </h3>
              <p className="text-[10px] text-gray-500">Secured with Supabase Auth</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-500 hover:text-white p-1.5 rounded-full hover:bg-white/5 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Mode Switcher Tabs */}
        <div className="grid grid-cols-2 gap-1.5 bg-black/50 p-1 rounded-2xl border border-white/[0.06] mb-4">
          <button
            type="button"
            onClick={() => {
              setMode("signup");
              setErrorMsg(null);
            }}
            className={`py-2 text-xs font-bold rounded-xl transition-all ${
              mode === "signup"
                ? "bg-green-500/20 text-green-400 border border-green-500/30 shadow-[0_0_10px_rgba(34,197,94,0.1)]"
                : "text-gray-400 hover:text-white"
            }`}
          >
            Create Account
          </button>
          <button
            type="button"
            onClick={() => {
              setMode("signin");
              setErrorMsg(null);
            }}
            className={`py-2 text-xs font-bold rounded-xl transition-all ${
              mode === "signin"
                ? "bg-green-500/20 text-green-400 border border-green-500/30 shadow-[0_0_10px_rgba(34,197,94,0.1)]"
                : "text-gray-400 hover:text-white"
            }`}
          >
            Sign In
          </button>
        </div>

        {/* Error Notification */}
        {errorMsg && (
          <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-medium">
            {errorMsg}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-3.5 text-left">
          {mode === "signup" && (
            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-1">Full Name</label>
              <div className="relative">
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Jimmy Muema"
                  className="w-full bg-black/60 border border-white/[0.08] rounded-xl pl-9 pr-3 py-2.5 text-xs text-white placeholder-gray-600 focus:outline-none focus:border-green-500 transition-colors"
                />
                <User className="w-4 h-4 text-gray-500 absolute left-3 top-3" />
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-gray-400 mb-1">Email Address</label>
            <div className="relative">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@domain.com"
                required
                className="w-full bg-black/60 border border-white/[0.08] rounded-xl pl-9 pr-3 py-2.5 text-xs font-mono text-white placeholder-gray-600 focus:outline-none focus:border-green-500 transition-colors"
              />
              <Mail className="w-4 h-4 text-gray-500 absolute left-3 top-3" />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-400 mb-1">Password</label>
            <div className="relative">
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                required
                className="w-full bg-black/60 border border-white/[0.08] rounded-xl pl-9 pr-3 py-2.5 text-xs font-mono text-white placeholder-gray-600 focus:outline-none focus:border-green-500 transition-colors"
              />
              <Lock className="w-4 h-4 text-gray-500 absolute left-3 top-3" />
            </div>
          </div>

          <div className="flex items-center gap-2 pt-1 text-[11px] text-gray-500">
            <ShieldCheck className="w-3.5 h-3.5 text-green-400" />
            <span>Profile stored directly in Supabase database</span>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3.5 bg-gradient-to-r from-green-500 to-green-600 hover:from-green-400 hover:to-green-500 text-black font-extrabold text-xs rounded-2xl shadow-[0_4px_20px_rgba(34,197,94,0.3)] transition-all flex items-center justify-center gap-2 cursor-pointer active:scale-[0.98] disabled:opacity-50"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-black border-t-transparent rounded-full animate-spin" />
            ) : (
              <>
                <span>{mode === "signup" ? "⚡ CREATE ACCOUNT & LAUNCH" : "🔓 SIGN IN TO COCKPIT"}</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
};
