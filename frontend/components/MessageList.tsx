"use client";

import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";
import TypingIndicator from "./TypingIndicator";
import type { ChatMessage } from "@/lib/types";

type Props = {
  messages: ChatMessage[];
  waiting: boolean;
};

export default function MessageList({ messages, waiting }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, waiting]);

  return (
    <div className="flex-1 space-y-3 overflow-y-auto px-5 py-5">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
      {waiting ? <TypingIndicator /> : null}
      <div ref={bottomRef} />
    </div>
  );
}
