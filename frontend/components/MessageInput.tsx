"use client";

import { KeyboardEvent, useState } from "react";

type Props = {
  disabled: boolean;
  onSend: (content: string) => void;
};

export default function MessageInput({ disabled, onSend }: Props) {
  const [value, setValue] = useState("");

  const submit = () => {
    const content = value.trim();
    if (!content || disabled) {
      return;
    }
    onSend(content);
    setValue("");
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <form
      className="border-t border-slate-200/80 bg-white px-5 py-4"
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
    >
      <div className="flex items-end gap-3">
        <textarea
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={onKeyDown}
          disabled={disabled}
          rows={2}
          placeholder="入力してください"
          className="min-h-[72px] flex-1 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm leading-6 outline-none ring-bubble-user/20 transition focus:border-bubble-user focus:bg-white focus:ring-4 disabled:cursor-not-allowed disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className="h-11 rounded-full bg-bubble-user px-5 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          送信
        </button>
      </div>
      <p className="mt-2 text-[11px] text-muted">Enter で送信 / Shift + Enter で改行</p>
    </form>
  );
}
