import type { ChatMessage } from "@/lib/types";

type Props = {
  message: ChatMessage;
};

export default function MessageBubble({ message }: Props) {
  const isUser = message.sender === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[78%] rounded-2xl px-4 py-3 text-sm leading-7 shadow-sm ${
          isUser
            ? "rounded-br-md bg-bubble-user text-white"
            : "rounded-bl-md bg-bubble-agent text-ink"
        }`}
      >
        {message.content}
      </div>
    </div>
  );
}
