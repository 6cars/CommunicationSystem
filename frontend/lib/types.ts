export type Sender = "user" | "agent";

export type AuthUser = {
  role: "user" | "admin";
  user_id: string;
  name: string;
};

export type ResponseType = "answer" | "dont_know" | "nothing";

export type ChatMessage = {
  id: string;
  sender: Sender;
  content: string;
  phase?: string;
  element?: string;
  response_type?: ResponseType | "";
  kind?: string;
  created_at: string;
};

// 入力エリアの表示を決める情報（free: 自由入力 / yes_no: はい・いいえ / closed: 対話終了）
export type InputState = {
  mode: "free" | "yes_no" | "closed";
  state: string;
  state_label: string;
  phase: string;
  required: boolean;
};

export type SessionStartResponse = {
  session_id: string;
  user_id: string;
  created_at: string;
  current_phase: string;
  initial_messages: ChatMessage[];
  input_state: InputState;
};

export type SendMessageResponse = {
  user_message: ChatMessage;
  agent_messages: ChatMessage[];
  input_state: InputState;
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
  phase: string;
  phase_label: string;
  element: string;
  element_label: string;
  response_type: string;
  response_type_label: string;
  kind: string;
  created_at: string;
};

export type ExperienceRecord = {
  id: number;
  kind: "failure" | "related";
  relation_type: 1 | 2 | null;
  action: string;
  pre_states: string[];
  post_states: string[];
  pre_thought: string;
  post_thought: string;
  pre_state_and_action: string;
  evaluation: boolean | null;
};

export type AdminSessionDetail = {
  session_id: string;
  user_id: string;
  user_name: string;
  created_at: string;
  updated_at: string;
  current_phase: string;
  completed: boolean;
  messages: AdminMessageDetail[];
  failure_experience: ExperienceRecord | null;
  related_experiences: ExperienceRecord[];
};
