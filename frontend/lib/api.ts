import type { ChatMessage, SendMessageResponse, SessionStartResponse } from "./types";

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
    const detail = await response.text();
    throw new Error(detail || `API error ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function createSession() {
  return request<SessionStartResponse>("/api/sessions/", { method: "POST" });
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
