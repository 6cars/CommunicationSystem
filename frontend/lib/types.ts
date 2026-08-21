export type Sender = "user" | "agent";

export type AuthUser = {
  role: "user" | "admin";
  user_id: string;
  name: string;
};

export type ChatMessage = {
  id: string;
  sender: Sender;
  content: string;
  created_at: string;
};

export type SessionStartResponse = {
  session_id: string;
  user_id: string;
  created_at: string;
  current_phase: string;
  initial_message: string;
};

export type SendMessageResponse = {
  user_message: ChatMessage;
  agent_message: ChatMessage;
  strategy_info: {
    phase?: string;
    intent?: string;
    engine?: string;
  };
};

export type AdminUserSummary = {
  user_id: string;
  name: string;
  is_admin: boolean;
  session_count: number;
  message_count: number;
  last_activity: string | null;
  created_at: string;
};

export type AdminSessionSummary = {
  session_id: string;
  user_id: string;
  user_name: string;
  created_at: string;
  updated_at: string;
  current_phase: string;
  message_count: number;
  preview_text: string;
};

export type AdminMessageDetail = {
  id: string;
  sender: Sender;
  content: string;
  strategy_log?: Record<string, unknown> | null;
  created_at: string;
};

export type AdminSessionDetail = {
  session_id: string;
  user_id: string;
  user_name: string;
  created_at: string;
  updated_at: string;
  current_phase: string;
  messages: AdminMessageDetail[];
};
