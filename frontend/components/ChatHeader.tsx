"use client";

type Props = {
  userId?: string;
  name?: string;
  isAdmin?: boolean;
  onReset: () => void;
  onLogout: () => void;
  onBackToAdmin?: () => void;
  disabled: boolean;
};

export default function ChatHeader({
  userId,
  name,
  isAdmin,
  onReset,
  onLogout,
  onBackToAdmin,
  disabled,
}: Props) {
  return (
    <header className="flex items-center justify-between gap-4 border-b border-slate-200/80 px-5 py-4">
      <div>
        <div className="flex items-center gap-2">
          <p className="text-[11px] font-medium uppercase tracking-[0.22em] text-muted">
            Counseling Dialogue
          </p>
          {name && (
            <span className="rounded bg-blue-50 px-2.5 py-0.5 text-[11px] font-semibold text-blue-700">
              ユーザー: {name}
            </span>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2">
        {isAdmin && onBackToAdmin && (
          <button
            type="button"
            onClick={onBackToAdmin}
            className="rounded-full border border-slate-800 bg-slate-900 px-3.5 py-1.5 text-xs font-semibold text-white transition hover:bg-slate-800"
          >
            管理者画面へ
          </button>
        )}
        <button
          type="button"
          onClick={onReset}
          disabled={disabled}
          className="rounded-full border border-slate-300 bg-white px-3.5 py-1.5 text-xs font-medium text-ink transition hover:border-slate-400 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          会話をリセット
        </button>
        <button
          type="button"
          onClick={onLogout}
          className="rounded-full border border-slate-200 bg-slate-100 px-3.5 py-1.5 text-xs font-medium text-slate-600 transition hover:bg-slate-200"
        >
          ログアウト
        </button>
      </div>
    </header>
  );
}
