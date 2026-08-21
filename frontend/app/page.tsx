"use client";

import { useCallback, useEffect, useState } from "react";
import AdminDashboard from "@/components/AdminDashboard";
import ChatHeader from "@/components/ChatHeader";
import LoginCard from "@/components/LoginCard";
import MessageInput from "@/components/MessageInput";
import MessageList from "@/components/MessageList";
import { createSession, sendMessage } from "@/lib/api";
import type { AuthUser, ChatMessage } from "@/lib/types";

const AUTH_STORAGE_KEY = "counseling_auth_user";

export default function HomePage() {
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [adminView, setAdminView] = useState<"dashboard" | "chat">("dashboard");
  const [isInitialized, setIsInitialized] = useState(false);

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [waiting, setWaiting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 初回マウント時に localStorage からログイン情報を復元
  useEffect(() => {
    try {
      const stored = localStorage.getItem(AUTH_STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as AuthUser;
        setCurrentUser(parsed);
      }
    } catch {
      // ignore
    } finally {
      setIsInitialized(true);
    }
  }, []);

  const handleLogin = (user: AuthUser) => {
    setCurrentUser(user);
    try {
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(user));
    } catch {
      // ignore
    }
    if (user.role === "admin") {
      setAdminView("dashboard");
    }
  };

  const handleLogout = () => {
    setCurrentUser(null);
    setSessionId(null);
    setMessages([]);
    try {
      localStorage.removeItem(AUTH_STORAGE_KEY);
    } catch {
      // ignore
    }
  };

  const startSession = useCallback(async (userId?: string) => {
    setWaiting(true);
    setError(null);
    setMessages([]);
    setSessionId(null);
    try {
      const session = await createSession(userId || "guest");
      setSessionId(session.session_id);
      setMessages([
        {
          id: "initial",
          sender: "agent",
          content: session.initial_message,
          created_at: session.created_at,
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "セッションを開始できませんでした");
    } finally {
      setWaiting(false);
    }
  }, []);

  // ユーザーがチャット画面に入ったときに自動でセッション開始
  useEffect(() => {
    if (currentUser) {
      if (currentUser.role === "user" || adminView === "chat") {
        void startSession(currentUser.user_id);
      }
    }
  }, [currentUser, adminView, startSession]);

  const onSend = async (content: string) => {
    if (!sessionId || waiting) {
      return;
    }
    setWaiting(true);
    setError(null);
    try {
      const result = await sendMessage(sessionId, content);
      setMessages((current) => [...current, result.user_message, result.agent_message]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "送信に失敗しました");
    } finally {
      setWaiting(false);
    }
  };

  if (!isInitialized) {
    return null;
  }

  // 1. 未ログインの場合: ログイン画面を表示
  if (!currentUser) {
    return (
      <main className="flex min-h-screen items-center justify-center p-4 bg-slate-100">
        <LoginCard onLogin={handleLogin} />
      </main>
    );
  }

  // 2. 管理者ログインかつダッシュボード表示の場合
  if (currentUser.role === "admin" && adminView === "dashboard") {
    return (
      <AdminDashboard
        adminUser={currentUser}
        onLogout={handleLogout}
        onGoToChat={() => setAdminView("chat")}
      />
    );
  }

  // 3. 一般ユーザー または 管理者のチャットテスト画面
  const inputDisabled = waiting || !sessionId;

  return (
    <main className="flex min-h-screen items-center justify-center p-4 md:p-8 bg-slate-100">
      <section className="flex h-[min(840px,calc(100vh-2rem))] w-full max-w-3xl flex-col overflow-hidden rounded-[28px] bg-white shadow-panel">
        <ChatHeader
          userId={currentUser.user_id}
          name={currentUser.name}
          isAdmin={currentUser.role === "admin"}
          onReset={() => void startSession(currentUser.user_id)}
          onLogout={handleLogout}
          onBackToAdmin={() => setAdminView("dashboard")}
          disabled={waiting}
        />
        {error ? (
          <p className="border-b border-red-100 bg-red-50 px-5 py-2 text-sm text-red-700">{error}</p>
        ) : null}
        {waiting && messages.length === 0 ? (
          <div className="flex flex-1 items-center justify-center text-sm text-muted">
            セッションを準備しています...
          </div>
        ) : (
          <MessageList messages={messages} waiting={waiting && messages.length > 0} />
        )}
        <MessageInput disabled={inputDisabled} onSend={(content) => void onSend(content)} />
      </section>
    </main>
  );
}
