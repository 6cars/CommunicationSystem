import type {
  AdminSessionDetail,
  AdminSessionSummary,
  AdminUserSummary,
  AuthUser,
  ChatMessage,
  SendMessageResponse,
  SessionStartResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    let errorMsg = `API error ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        errorMsg = errJson.detail;
      }
    } catch {
      const detail = await response.text();
      if (detail) {
        errorMsg = detail;
      }
    }
    throw new Error(errorMsg);
  }

  return response.json() as Promise<T>;
}

export function register(payload: { name: string; password: string }) {
  return request<AuthUser>("/api/auth/register/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function login(payload: { name: string; password: string }) {
  return request<AuthUser>("/api/auth/login/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createSession(userId?: string, name?: string) {
  return request<SessionStartResponse>("/api/sessions/", {
    method: "POST",
    body: JSON.stringify({ user_id: userId || "guest", name }),
  });
}

export function fetchMessages(sessionId: string) {
  return request<ChatMessage[]>(`/api/sessions/${sessionId}/messages/`);
}

export function sendMessage(sessionId: string, content: string) {
  return request<SendMessageResponse>(`/api/sessions/${sessionId}/messages/`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export function fetchAdminUsers() {
  return request<AdminUserSummary[]>("/api/admin/users/");
}

export function deleteAdminUser(userId: string) {
  return request<{ success: boolean; detail: string }>(`/api/admin/users/${encodeURIComponent(userId)}/`, {
    method: "DELETE",
  });
}

export function fetchAdminUserSessions(userId: string) {
  return request<AdminSessionSummary[]>(`/api/admin/users/${encodeURIComponent(userId)}/sessions/`);
}

export function fetchAdminSessionMessages(sessionId: string) {
  return request<AdminSessionDetail>(`/api/admin/sessions/${sessionId}/messages/`);
}

/**
 * 経験想起支援API（プレースホルダー）
 * 何も思いつかなかった時にプロンプトを作成して生成AIに投げて具体例を出力する機能用
 */
export function requestRecallSupport(sessionId: string, payload?: Record<string, unknown>) {
  // TODO: 生成AI連携用のバックエンドエンドポイントを呼び出す際に有効化
  return request<{ user_message?: ChatMessage; agent_message?: ChatMessage; examples?: string[] }>(
    `/api/sessions/${sessionId}/recall-support/`,
    {
      method: "POST",
      body: JSON.stringify(payload ?? {}),
    }
  );
}
