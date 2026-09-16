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

  const startSession = useCallback(async (userId?: string, name?: string) => {
    setWaiting(true);
    setError(null);
    setMessages([]);
    setSessionId(null);
    try {
      const session = await createSession(userId || "guest", name);
      setSessionId(session.session_id);
      const initialMsgs =
        session.initial_messages && session.initial_messages.length > 0
          ? session.initial_messages
          : [
              {
                id: "initial",
                sender: "agent" as const,
                content: session.initial_message,
                created_at: session.created_at,
              },
            ];

      // 各メッセージを表示する前に「入力中」を約2秒（2000ms）見せる
      for (let i = 0; i < initialMsgs.length; i++) {
        setWaiting(true);
        await new Promise((resolve) => setTimeout(resolve, 2000));
        setMessages((prev) => [...prev, initialMsgs[i]]);
      }
      setWaiting(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "セッションを開始できませんでした");
      setWaiting(false);
    }
  }, []);

  // ユーザーがチャット画面に入ったときに自動でセッション開始
  useEffect(() => {
    if (currentUser) {
      if (currentUser.role === "user" || adminView === "chat") {
        void startSession(currentUser.user_id, currentUser.name);
      }
    }
  }, [currentUser, adminView, startSession]);

  const onSend = async (content: string) => {
    if (!sessionId || waiting) {
      return;
    }
    setWaiting(true);
    setError(null);

    // ユーザー側のメッセージを即座に表示
    const tempUserId = `temp-user-${Date.now()}`;
    setMessages((current) => [
      ...current,
      {
        id: tempUserId,
        sender: "user",
        content,
        created_at: new Date().toISOString(),
      },
    ]);

    try {
      // API送信と「入力中」の約2秒ウェイトを並行して待機
      const [result] = await Promise.all([
        sendMessage(sessionId, content),
        new Promise((resolve) => setTimeout(resolve, 2000)),
      ]);

      const agentMsgs: ChatMessage[] =
        result.agent_messages && result.agent_messages.length > 0
          ? result.agent_messages
          : [result.agent_message];

      // 1通目を表示
      setMessages((current) => {
        const withoutTemp = current.filter((m) => m.id !== tempUserId);
        return [...withoutTemp, result.user_message, agentMsgs[0]];
      });

      // 2通目以降がある場合は、2秒の入力中アニメーションを挟んで連続表示
      for (let i = 1; i < agentMsgs.length; i++) {
        setWaiting(true);
        await new Promise((resolve) => setTimeout(resolve, 2000));
        setMessages((current) => [...current, agentMsgs[i]]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "送信に失敗しました");
      setMessages((current) => current.filter((m) => m.id !== tempUserId));
    } finally {
      setWaiting(false);
    }
  };

  // 経験想起支援（「思い当たらない」ボタン押下時の処理）
  const handleRecallSupport = async () => {
    if (!sessionId || waiting) {
      return;
    }
    console.log("[経験想起支援] 「思い当たらない」ボタンが押下されました。");

    // TODO: 将来ここにプロンプト作成・生成AIによる具体例取得の処理を追加可能
    // 現状は「思い当たらない」という入力を対話エンジンに送信し、対話フローを次に進めます
    await onSend("思い当たらない");
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
          onReset={() => void startSession(currentUser.user_id, currentUser.name)}
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
        <MessageInput
          disabled={inputDisabled}
          onSend={(content) => void onSend(content)}
          onRecallSupport={() => void handleRecallSupport()}
        />
      </section>
    </main>
  );
}
