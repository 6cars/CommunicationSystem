"use client";

import { useState } from "react";
import { login, register } from "@/lib/api";
import type { AuthUser } from "@/lib/types";

type Props = {
  onLogin: (user: AuthUser) => void;
};

export default function LoginCard({ onLogin }: Props) {
  const [mode, setMode] = useState<"login" | "register">("login");

  // Login form state
  const [loginName, setLoginName] = useState("");
  const [loginPassword, setLoginPassword] = useState("");

  // Register form state
  const [regName, setRegName] = useState("");
  const [regPassword, setRegPassword] = useState("");
  const [regPasswordConfirm, setRegPasswordConfirm] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loginName.trim()) {
      setError("お名前を入力してください");
      return;
    }
    if (!loginPassword.trim()) {
      setError("パスワードを入力してください");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await login({
        name: loginName.trim(),
        password: loginPassword.trim(),
      });
      onLogin(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "ログインに失敗しました");
    } finally {
      setLoading(false);
    }
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!regName.trim()) {
      setError("お名前を入力してください");
      return;
    }
    if (!regPassword.trim()) {
      setError("パスワードを入力してください");
      return;
    }
    if (regPassword !== regPasswordConfirm) {
      setError("パスワードと確認用パスワードが一致しません");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await register({
        name: regName.trim(),
        password: regPassword.trim(),
      });
      onLogin(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "新規登録に失敗しました");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md rounded-3xl bg-white p-8 shadow-panel border border-slate-100">
      <div className="text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-blue-600">
          Counseling Dialogue System
        </p>
        <h2 className="mt-2 text-2xl font-bold text-slate-800">
          {mode === "login" ? "ログイン" : "新規アカウント登録"}
        </h2>
        <p className="mt-1 text-xs text-slate-500">
          {mode === "login"
            ? "お名前とパスワードを入力してログインしてください"
            : "お名前とパスワードを登録してチャットを開始します"}
        </p>
      </div>

      {error && (
        <div className="mt-5 rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700">
          {error}
        </div>
      )}

      {mode === "login" ? (
        <form onSubmit={handleLoginSubmit} className="mt-6 space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-700">お名前</label>
            <input
              type="text"
              value={loginName}
              onChange={(e) => setLoginName(e.target.value)}
              placeholder="お名前を入力"
              className="mt-1.5 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm outline-none transition focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-100"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700">パスワード</label>
            <input
              type="password"
              value={loginPassword}
              onChange={(e) => setLoginPassword(e.target.value)}
              placeholder="パスワードを入力"
              className="mt-1.5 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm outline-none transition focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-100"
            />
          </div>

          <button
            type="submit"
            disabled={loading || !loginName.trim() || !loginPassword.trim()}
            className="w-full rounded-xl bg-blue-600 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300 shadow-sm"
          >
            {loading ? "ログイン中..." : "ログイン"}
          </button>

          <div className="pt-3 text-center">
            <button
              type="button"
              onClick={() => {
                setMode("register");
                setError(null);
              }}
              className="text-xs text-blue-600 hover:underline font-medium"
            >
              アカウントをお持ちでない方は <span className="font-bold">新規登録</span>
            </button>
          </div>
        </form>
      ) : (
        <form onSubmit={handleRegisterSubmit} className="mt-6 space-y-3.5">
          <div>
            <label className="block text-xs font-medium text-slate-700">お名前</label>
            <input
              type="text"
              value={regName}
              onChange={(e) => setRegName(e.target.value)}
              placeholder="例: 田中 太郎"
              className="mt-1.5 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm outline-none transition focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-100"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700">パスワード</label>
            <input
              type="password"
              value={regPassword}
              onChange={(e) => setRegPassword(e.target.value)}
              placeholder="パスワードを入力"
              className="mt-1.5 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm outline-none transition focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-100"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700">パスワード (確認用)</label>
            <input
              type="password"
              value={regPasswordConfirm}
              onChange={(e) => setRegPasswordConfirm(e.target.value)}
              placeholder="もう一度パスワードを入力"
              className="mt-1.5 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm outline-none transition focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-100"
            />
          </div>

          <button
            type="submit"
            disabled={
              loading ||
              !regName.trim() ||
              !regPassword.trim() ||
              !regPasswordConfirm.trim()
            }
            className="w-full rounded-xl bg-blue-600 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300 shadow-sm mt-2"
          >
            {loading ? "登録中..." : "登録してチャットを開始"}
          </button>

          <div className="pt-3 text-center">
            <button
              type="button"
              onClick={() => {
                setMode("login");
                setError(null);
              }}
              className="text-xs text-blue-600 hover:underline font-medium"
            >
              すでにアカウントをお持ちの方は <span className="font-bold">ログイン</span>
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
