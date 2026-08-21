export type Sender = "user" | "agent";

export type ChatMessage = {
  id: string;
  sender: Sender;
  content: string;
  created_at: string;
};

export type SessionStartResponse = {
  session_id: string;
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
