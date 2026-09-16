"use client";

import { KeyboardEvent, useState } from "react";

type Props = {
  disabled: boolean;
  onSend: (content: string) => void;
  onRecallSupport?: () => void;
};

export default function MessageInput({ disabled, onSend, onRecallSupport }: Props) {
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
      {/* 補助アクションバー */}
      <div className="mb-2.5 flex items-center justify-between">
        {onRecallSupport && (
          <button
            type="button"
            onClick={onRecallSupport}
            disabled={disabled}
            className="inline-flex items-center gap-1.5 rounded-full border border-amber-200 bg-amber-50/90 px-3.5 py-1.5 text-xs font-medium text-amber-800 transition hover:bg-amber-100 hover:border-amber-300 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50 shadow-sm"
            title="何も思いつかない時に具体例を出力して想起を支援します"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="h-3.5 w-3.5 text-amber-600"
            >
              <path
                d="M10 2a6 6 0 00-6 6c0 1.887.87 3.57 2.235 4.673A2.002 2.002 0 007 14.25v.75a1 1 0 001 1h4a1 1 0 001-1v-.75a2.002 2.002 0 00.765-1.577A6.002 6.002 0 0016 8a6 6 0 00-6-6zm-1.5 16a1.5 1.5 0 003 0h-3z"
              />
            </svg>
            <span>思い当たらない</span>
          </button>
        )}
        <p className="text-[11px] text-muted ml-auto">Enter で送信 / Shift + Enter で改行</p>
      </div>

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
    </form>
  );
}
