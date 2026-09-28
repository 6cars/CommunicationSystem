"use client";

import { KeyboardEvent, useState } from "react";
import type { InputState } from "@/lib/types";

type Props = {
  disabled: boolean;
  inputState: InputState | null;
  onAnswer: (content: string) => void;
  onDontKnow: () => void;
  onNothing: () => void;
};

export default function MessageInput({ disabled, inputState, onAnswer, onDontKnow, onNothing }: Props) {
  const [value, setValue] = useState("");
  const mode = inputState?.mode ?? "free";
  const required = inputState?.required ?? false;

  const submit = () => {
    const content = value.trim();
    if (!content || disabled) {
      return;
    }
    onAnswer(content);
    setValue("");
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit();
    }
  };

  if (mode === "closed") {
    return (
      <div className="border-t border-slate-200/80 bg-slate-50 px-5 py-5 text-center text-sm text-muted">
        対話は終了しました。新しく始める場合は「会話をリセット」を押してください。
      </div>
    );
  }

  // 評価の質問: 「はい」「いいえ」で答える
  if (mode === "yes_no") {
    return (
      <div className="border-t border-slate-200/80 bg-white px-5 py-5">
        <div className="flex justify-center gap-4">
          {["はい", "いいえ"].map((label) => (
            <button
              key={label}
              type="button"
              onClick={() => onAnswer(label)}
              disabled={disabled}
              className="h-12 w-36 rounded-full border border-bubble-user bg-white text-sm font-semibold text-bubble-user shadow-sm transition hover:bg-blue-50 active:scale-95 disabled:cursor-not-allowed disabled:border-slate-300 disabled:text-slate-400"
            >
              {label}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <form
      className="border-t border-slate-200/80 bg-white px-5 py-4"
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
    >
      {/* 補助アクションバー: 想起できないときのボタン */}
      <div className="mb-2.5 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={onDontKnow}
          disabled={disabled}
          className="inline-flex items-center gap-1 rounded-full border border-amber-300 bg-amber-50 px-3 py-1 text-xs font-medium text-amber-800 transition hover:bg-amber-100 hover:border-amber-400 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50 shadow-sm"
          title="回答の具体例を提示します"
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
          <span>思いつかない</span>
        </button>

        <button
          type="button"
          onClick={onNothing}
          disabled={disabled || required}
          className="inline-flex items-center gap-1 rounded-full border border-slate-300 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700 transition hover:bg-slate-100 hover:border-slate-400 active:scale-95 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400 disabled:line-through disabled:shadow-none disabled:active:scale-100 shadow-sm"
          title={required ? "この質問は省略できません" : "この質問に答えずに次へ進みます"}
        >
          <span>特にない</span>
        </button>
        {required ? <span className="text-[11px] text-slate-400">この質問は省略できません</span> : null}

        <p className="text-[11px] text-muted ml-auto hidden sm:block">Enter で送信 / Shift + Enter で改行</p>
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
