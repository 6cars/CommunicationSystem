"use client";

type Props = {
  phase: string | null;
  onReset: () => void;
  disabled: boolean;
};

const PHASE_LABELS: Record<string, string> = {
  initial: "導入",
  active_listening: "傾聴",
  exploring: "探索",
};

export default function ChatHeader({ phase, onReset, disabled }: Props) {
  const phaseLabel = phase ? PHASE_LABELS[phase] ?? phase : "準備中";

  return (
    <header className="flex items-center justify-between gap-4 border-b border-slate-200/80 px-5 py-4">
      <div>
        <p className="text-[11px] font-medium uppercase tracking-[0.22em] text-muted">
          Counseling Dialogue
        </p>
        <h1 className="mt-1 text-lg font-semibold tracking-tight">カウンセリング対話エージェント</h1>
        <p className="mt-1 text-xs text-muted">
          対話フェーズ: <span className="font-medium text-ink">{phaseLabel}</span>
        </p>
      </div>
      <button
        type="button"
        onClick={onReset}
        disabled={disabled}
        className="rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-ink transition hover:border-slate-400 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
      >
        会話をリセット
      </button>
    </header>
  );
}
