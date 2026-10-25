"use client";

import type { LogMode } from "@/lib/types";

const OPTIONS: { mode: LogMode; title: string; description: string }[] = [
  {
    mode: "full",
    title: "ログを取る",
    description: "質問とあなたの回答をすべて記録します。研究のための分析に使用します。",
  },
  {
    mode: "anonymous",
    title: "ログを取らない（匿名）",
    description:
      "記録するのはシステムがどのような質問をしたかだけです。あなたの回答や、質問に含まれる回答の内容、提示された具体例はすべて「※」に置き換えて記録し、保存しません。",
  },
];

type Props = {
  onSelect: (mode: LogMode) => void;
  onLogout: () => void;
  onBackToAdmin?: () => void;
};

export default function LogModeSelector({ onSelect, onLogout, onBackToAdmin }: Props) {
  return (
    <div className="w-full max-w-md rounded-3xl bg-white p-8 shadow-panel border border-slate-100">
      <div className="text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-blue-600">
          Counseling Dialogue System
        </p>
        <h2 className="mt-2 text-2xl font-bold text-slate-800">記録の方法を選んでください</h2>
        <p className="mt-1 text-xs text-slate-500">会話を始める前に、対話の内容を記録するかどうかを選べます</p>
      </div>

      <div className="mt-6 space-y-3">
        {OPTIONS.map((option) => (
          <button
            key={option.mode}
            type="button"
            onClick={() => onSelect(option.mode)}
            className="w-full rounded-2xl border border-slate-200 bg-slate-50 p-4 text-left transition hover:border-blue-400 hover:bg-blue-50 focus:outline-none focus:ring-4 focus:ring-blue-100"
          >
            <span className="block text-sm font-bold text-slate-800">{option.title}</span>
            <span className="mt-1 block text-xs leading-relaxed text-slate-500">{option.description}</span>
          </button>
        ))}
      </div>

      <div className="mt-6 flex justify-center gap-4">
        {onBackToAdmin && (
          <button type="button" onClick={onBackToAdmin} className="text-xs text-blue-600 hover:underline font-medium">
            管理者画面へ
          </button>
        )}
        <button type="button" onClick={onLogout} className="text-xs text-slate-500 hover:underline font-medium">
          ログアウト
        </button>
      </div>
    </div>
  );
}
