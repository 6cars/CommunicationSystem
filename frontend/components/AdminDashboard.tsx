import { useEffect, useState } from "react";
import {
  deleteAdminUser,
  fetchAdminSessionMessages,
  fetchAdminUsers,
  fetchAdminUserSessions,
} from "@/lib/api";
import type {
  AdminMessageDetail,
  AdminSessionDetail,
  AdminSessionSummary,
  AdminUserSummary,
  AuthUser,
} from "@/lib/types";

type Props = {
  adminUser: AuthUser;
  onLogout: () => void;
  onGoToChat: () => void;
};

export default function AdminDashboard({ adminUser, onLogout, onGoToChat }: Props) {
  const [users, setUsers] = useState<AdminUserSummary[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);

  const [sessions, setSessions] = useState<AdminSessionSummary[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);

  const [activeSessionDetail, setActiveSessionDetail] = useState<AdminSessionDetail | null>(null);

  const [loadingUsers, setLoadingUsers] = useState(false);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [deletingUserId, setDeletingUserId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // ユーザー一覧の取得
  const loadUsers = async () => {
    setLoadingUsers(true);
    setError(null);
    try {
      const data = await fetchAdminUsers();
      setUsers(data);
      if (data.length > 0) {
        if (!selectedUserId || !data.some((u) => u.user_id === selectedUserId)) {
          setSelectedUserId(data[0].user_id);
        }
      } else {
        setSelectedUserId(null);
        setSessions([]);
        setSelectedSessionId(null);
        setActiveSessionDetail(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "ユーザー一覧の取得に失敗しました");
    } finally {
      setLoadingUsers(false);
    }
  };

  useEffect(() => {
    void loadUsers();
  }, []);

  // ユーザー削除処理
  const handleDeleteUser = async (userId: string, userName: string) => {
    const ok = window.confirm(
      `「${userName}」のアカウントと、これまでのすべての対話ログを完全に削除しますか？\n（この操作は取り消せません）`
    );
    if (!ok) return;

    setDeletingUserId(userId);
    setError(null);
    try {
      await deleteAdminUser(userId);
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "ユーザーの削除に失敗しました");
    } finally {
      setDeletingUserId(null);
    }
  };

  // 選択中ユーザーのセッション一覧の取得
  useEffect(() => {
    if (!selectedUserId) {
      setSessions([]);
      setSelectedSessionId(null);
      setActiveSessionDetail(null);
      return;
    }
    const loadSessions = async () => {
      setLoadingSessions(true);
      try {
        const data = await fetchAdminUserSessions(selectedUserId);
        setSessions(data);
        if (data.length > 0) {
          setSelectedSessionId(data[0].session_id);
        } else {
          setSelectedSessionId(null);
          setActiveSessionDetail(null);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "セッション一覧の取得に失敗しました");
      } finally {
        setLoadingSessions(false);
      }
    };
    void loadSessions();
  }, [selectedUserId]);

  // 選択中セッションのメッセージログ取得
  useEffect(() => {
    if (!selectedSessionId) {
      setActiveSessionDetail(null);
      return;
    }
    const loadMessages = async () => {
      setLoadingMessages(true);
      try {
        const detail = await fetchAdminSessionMessages(selectedSessionId);
        setActiveSessionDetail(detail);
      } catch (err) {
        setError(err instanceof Error ? err.message : "対話ログの取得に失敗しました");
      } finally {
        setLoadingMessages(false);
      }
    };
    void loadMessages();
  }, [selectedSessionId]);

  const filteredUsers = users.filter((u) => {
    const query = searchQuery.toLowerCase();
    return (
      (u.name && u.name.toLowerCase().includes(query)) ||
      u.user_id.toLowerCase().includes(query)
    );
  });

  const selectedUser = users.find((u) => u.user_id === selectedUserId);

  const exportCurrentLog = () => {
    if (!activeSessionDetail) return;
    const blob = new Blob([JSON.stringify(activeSessionDetail, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `dialogue_log_${activeSessionDetail.user_name || "user"}_${activeSessionDetail.session_id.slice(
      0,
      8
    )}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex h-screen w-full flex-col bg-slate-100 text-slate-800">
      {/* 管理者ヘッダー */}
      <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-6 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-bold text-white tracking-wider">
            ADMIN
          </div>
          <h1 className="text-base font-bold text-slate-800">対話ログ・ユーザー管理ダッシュボード</h1>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-500">
            管理者: <span className="font-semibold text-slate-700">{adminUser.name || adminUser.user_id}</span>
          </span>
          <button
            type="button"
            onClick={onGoToChat}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50"
          >
            チャット画面を試す
          </button>
          <button
            type="button"
            onClick={onLogout}
            className="rounded-lg bg-red-50 border border-red-200 px-3 py-1.5 text-xs font-medium text-red-600 transition hover:bg-red-100"
          >
            ログアウト
          </button>
        </div>
      </header>

      {error && (
        <div className="bg-red-500 px-6 py-2 text-xs font-medium text-white flex justify-between items-center">
          <span>{error}</span>
          <button type="button" onClick={() => setError(null)} className="underline text-xs">
            閉じる
          </button>
        </div>
      )}

      {/* 3ペイン構成のメインエリア */}
      <div className="flex flex-1 overflow-hidden">
        {/* 1. ユーザー一覧ペイン */}
        <aside className="flex w-80 flex-col border-r border-slate-200 bg-white">
          <div className="p-4 border-b border-slate-100">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                ユーザー一覧 ({filteredUsers.length})
              </h2>
              <button
                type="button"
                onClick={loadUsers}
                disabled={loadingUsers}
                className="text-xs text-blue-600 hover:underline font-medium"
              >
                {loadingUsers ? "更新中..." : "更新"}
              </button>
            </div>
            <input
              type="text"
              placeholder="お名前で検索..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="mt-2 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs outline-none focus:border-blue-500 focus:bg-white focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
            {filteredUsers.length === 0 ? (
              <div className="p-6 text-center text-xs text-slate-400">
                登録ユーザーはいません
              </div>
            ) : (
              filteredUsers.map((u) => {
                const isSelected = selectedUserId === u.user_id;
                const isDeleting = deletingUserId === u.user_id;
                return (
                  <div
                    key={u.user_id}
                    className={`group relative flex items-center justify-between rounded-xl p-3 transition ${
                      isSelected
                        ? "bg-blue-50 border border-blue-200 shadow-sm"
                        : "hover:bg-slate-50 border border-transparent"
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => setSelectedUserId(u.user_id)}
                      className="flex-1 text-left"
                    >
                      <div className="flex items-center justify-between">
                        <span className={`text-sm font-bold ${isSelected ? "text-blue-700" : "text-slate-800"}`}>
                          {u.name}
                        </span>
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600">
                          {u.session_count} 会話
                        </span>
                      </div>
                      <div className="mt-1 flex items-center justify-between text-[11px] text-slate-400">
                        <span>メッセージ: {u.message_count}件</span>
                        <span>
                          {u.last_activity
                            ? new Date(u.last_activity).toLocaleDateString("ja-JP")
                            : "-"}
                        </span>
                      </div>
                    </button>

                    {/* 削除ボタン */}
                    <button
                      type="button"
                      title="アカウントと対話ログを削除"
                      disabled={isDeleting}
                      onClick={(e) => {
                        e.stopPropagation();
                        void handleDeleteUser(u.user_id, u.name);
                      }}
                      className="ml-2 rounded-lg p-1.5 text-slate-400 opacity-0 transition group-hover:opacity-100 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        className="h-4 w-4"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                        />
                      </svg>
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </aside>

        {/* 2. セッション一覧ペイン */}
        <section className="flex w-80 flex-col border-r border-slate-200 bg-slate-50">
          <div className="p-4 border-b border-slate-200 bg-white">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                会話セッション ({sessions.length})
              </h2>
              {selectedUser && (
                <button
                  type="button"
                  onClick={() => void handleDeleteUser(selectedUser.user_id, selectedUser.name)}
                  className="text-[11px] text-red-600 hover:underline font-medium"
                >
                  ユーザー削除
                </button>
              )}
            </div>
            <p className="mt-1 text-xs text-slate-700">
              対象ユーザー: <span className="font-bold">{selectedUser ? selectedUser.name : "-"}</span>
            </p>
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
            {loadingSessions ? (
              <div className="p-4 text-center text-xs text-slate-400">セッション読込中...</div>
            ) : sessions.length === 0 ? (
              <div className="p-4 text-center text-xs text-slate-400">
                セッション履歴がありません
              </div>
            ) : (
              sessions.map((s, idx) => {
                const isSelected = selectedSessionId === s.session_id;
                const dateStr = s.created_at
                  ? new Date(s.created_at).toLocaleString("ja-JP", {
                      month: "numeric",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })
                  : "-";
                return (
                  <button
                    key={s.session_id}
                    type="button"
                    onClick={() => setSelectedSessionId(s.session_id)}
                    className={`w-full rounded-xl p-3 text-left transition ${
                      isSelected
                        ? "bg-white border-2 border-blue-500 shadow-md"
                        : "bg-white border border-slate-200 hover:border-slate-300"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-semibold text-slate-600">
                        #{sessions.length - idx} • {dateStr}
                      </span>
                      <span className="text-[10px] text-slate-400">{s.message_count} 通</span>
                    </div>
                    <p className="mt-1 text-xs text-slate-700 line-clamp-2">
                      {s.preview_text}
                    </p>
                  </button>
                );
              })
            )}
          </div>
        </section>

        {/* 3. 対話ログ詳細ペイン */}
        <main className="flex flex-1 flex-col bg-white">
          {activeSessionDetail ? (
            <>
              <div className="flex items-center justify-between border-b border-slate-200 px-6 py-3 bg-slate-50/50">
                <div>
                  <h3 className="text-sm font-bold text-slate-800">
                    対話ログ詳細
                  </h3>
                  <p className="text-[11px] text-slate-400 font-mono">
                    Session ID: {activeSessionDetail.session_id}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={exportCurrentLog}
                    className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 transition"
                  >
                    JSON エクスポート
                  </button>
                </div>
              </div>

              {/* メッセージログタイムライン */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-slate-50/30">
                {loadingMessages ? (
                  <div className="text-center text-xs text-slate-400 py-10">ログ読込中...</div>
                ) : activeSessionDetail.messages.length === 0 ? (
                  <div className="text-center text-xs text-slate-400 py-10">メッセージがありません</div>
                ) : (
                  activeSessionDetail.messages.map((m) => {
                    const isUser = m.sender === "user";
                    const time = m.created_at
                      ? new Date(m.created_at).toLocaleTimeString("ja-JP", {
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit",
                        })
                      : "";

                    return (
                      <div
                        key={m.id}
                        className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}
                      >
                        <div className="flex items-center gap-2 mb-1 px-1">
                          <span
                            className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                              isUser
                                ? "bg-blue-100 text-blue-800"
                                : "bg-emerald-100 text-emerald-800"
                            }`}
                          >
                            {isUser
                              ? `ユーザー: ${activeSessionDetail.user_name || "ユーザー"}`
                              : "ボット (エージェント)"}
                          </span>
                          <span className="text-[10px] text-slate-400">{time}</span>
                        </div>

                        <div
                          className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm shadow-sm leading-relaxed whitespace-pre-wrap ${
                            isUser
                              ? "bg-blue-600 text-white rounded-tr-none"
                              : "bg-white border border-slate-200 text-slate-800 rounded-tl-none"
                          }`}
                        >
                          {m.content}
                        </div>

                        {/* エージェントの戦略メタデータログ表示（存在する場合） */}
                        {!isUser && m.strategy_log && Object.keys(m.strategy_log).length > 0 && (
                          <div className="mt-1 text-[10px] font-mono text-slate-400 px-1">
                            strategy: {JSON.stringify(m.strategy_log)}
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </>
          ) : (
            <div className="flex flex-1 flex-col items-center justify-center text-slate-400 p-8 text-center">
              <p className="text-sm font-medium">ユーザーまたはセッションを選択してください</p>
              <p className="mt-1 text-xs text-slate-400">
                左側のリストからユーザーを選択すると、対話ログが表示されます
              </p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
