"use client";

import { useCallback, useEffect, useState } from "react";
import AdminDashboard from "@/components/AdminDashboard";
import ChatHeader from "@/components/ChatHeader";
import LoginCard from "@/components/LoginCard";
import MessageInput from "@/components/MessageInput";
import MessageList from "@/components/MessageList";
import { createSession, sendResponse } from "@/lib/api";
import type { AuthUser, ChatMessage, InputState, ResponseType } from "@/lib/types";

const AUTH_STORAGE_KEY = "counseling_auth_user";

// エージェントの各発話を表示する前に「入力中」を見せる時間
const TYPING_DELAY_MS = 2000;

const RESPONSE_LABELS: Record<ResponseType, string> = {
  answer: "",
  dont_know: "思いつかない",
  nothing: "特にない",
};

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export default function HomePage() {
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [adminView, setAdminView] = useState<"dashboard" | "chat">("dashboard");
  const [isInitialized, setIsInitialized] = useState(false);

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputState, setInputState] = useState<InputState | null>(null);
  const [waiting, setWaiting] = useState(false);
  const [waitingLabel, setWaitingLabel] = useState("入力中...");
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

  // エージェントの発話を「入力中」を挟みながら1通ずつ表示する
  const showAgentMessages = async (agentMsgs: ChatMessage[], firstAlreadyWaited = false) => {
    setWaitingLabel("入力中...");
    for (let i = 0; i < agentMsgs.length; i++) {
      if (i > 0 || !firstAlreadyWaited) {
        setWaiting(true);
        await sleep(TYPING_DELAY_MS);
      }
      setMessages((prev) => [...prev, agentMsgs[i]]);
    }
  };

  const startSession = useCallback(async (userId?: string, name?: string) => {
    setWaiting(true);
    setError(null);
    setMessages([]);
    setSessionId(null);
    setInputState(null);
    try {
      const session = await createSession(userId || "guest", name);
      setSessionId(session.session_id);
      await showAgentMessages(session.initial_messages);
      setInputState(session.input_state);
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
        void startSession(currentUser.user_id, currentUser.name);
      }
    }
  }, [currentUser, adminView, startSession]);

  // ユーザの応答（回答 / 思いつかない / 特にない）を送る
  const respond = async (responseType: ResponseType, content = "") => {
    if (!sessionId || waiting) {
      return;
    }
    setWaiting(true);
    // 「思いつかない」では経験想起支援機能が LLM で具体例を生成する
    setWaitingLabel(responseType === "dont_know" ? "具体例を生成しています..." : "入力中...");
    setError(null);

    // ユーザー側のメッセージを即座に表示
    const tempUserId = `temp-user-${Date.now()}`;
    setMessages((current) => [
      ...current,
      {
        id: tempUserId,
        sender: "user",
        content: content || RESPONSE_LABELS[responseType],
        created_at: new Date().toISOString(),
      },
    ]);

    try {
      const [result] = await Promise.all([sendResponse(sessionId, responseType, content), sleep(TYPING_DELAY_MS)]);
      setMessages((current) => [...current.filter((m) => m.id !== tempUserId), result.user_message]);
      await showAgentMessages(result.agent_messages, true);
      setInputState(result.input_state);
    } catch (err) {
      setError(err instanceof Error ? err.message : "送信に失敗しました");
      setMessages((current) => current.filter((m) => m.id !== tempUserId));
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
          <MessageList
            messages={messages}
            waiting={waiting && messages.length > 0}
            waitingLabel={waitingLabel}
          />
        )}
        <MessageInput
          disabled={inputDisabled}
          inputState={inputState}
          onAnswer={(content) => void respond("answer", content)}
          onDontKnow={() => void respond("dont_know")}
          onNothing={() => void respond("nothing")}
        />
      </section>
    </main>
  );
}
