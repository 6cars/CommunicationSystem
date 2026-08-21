"use client";

import { useCallback, useEffect, useState } from "react";
import ChatHeader from "@/components/ChatHeader";
import MessageInput from "@/components/MessageInput";
import MessageList from "@/components/MessageList";
import { createSession, sendMessage } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";

export default function HomePage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [phase, setPhase] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [waiting, setWaiting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startSession = useCallback(async () => {
    setWaiting(true);
    setError(null);
    setMessages([]);
    setSessionId(null);
    try {
      const session = await createSession();
      setSessionId(session.session_id);
      setPhase(session.current_phase);
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

  useEffect(() => {
    void startSession();
  }, [startSession]);

  const onSend = async (content: string) => {
    if (!sessionId || waiting) {
      return;
    }
    setWaiting(true);
    setError(null);
    try {
      const result = await sendMessage(sessionId, content);
      setMessages((current) => [...current, result.user_message, result.agent_message]);
      if (result.strategy_info.phase) {
        setPhase(result.strategy_info.phase);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "送信に失敗しました");
    } finally {
      setWaiting(false);
    }
  };

  const inputDisabled = waiting || !sessionId;

  return (
    <main className="flex min-h-screen items-center justify-center p-4 md:p-8">
      <section className="flex h-[min(840px,calc(100vh-2rem))] w-full max-w-3xl flex-col overflow-hidden rounded-[28px] bg-white shadow-panel">
        <ChatHeader phase={phase} onReset={() => void startSession()} disabled={waiting} />
        {error ? (
          <p className="border-b border-red-100 bg-red-50 px-5 py-2 text-sm text-red-700">{error}</p>
        ) : null}
        {waiting && messages.length === 0 ? (
          <div className="flex flex-1 items-center justify-center text-sm text-muted">セッションを準備しています...</div>
        ) : (
          <MessageList messages={messages} waiting={waiting && messages.length > 0} />
        )}
        <MessageInput disabled={inputDisabled} onSend={(content) => void onSend(content)} />
      </section>
    </main>
  );
}
