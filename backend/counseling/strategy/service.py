from counseling.strategy.base import BaseDialogueStrategy
from counseling.strategy.registry import load_strategy


class DialogueStrategyService:
    """セッション状態の更新と戦略エンジン呼び出しを仲介する。"""

    def __init__(self, strategy: BaseDialogueStrategy | None = None):
        self.strategy = strategy or load_strategy()

    def start_session(self, session, user_name: str = "") -> list[str]:
        if hasattr(self.strategy, "get_initial_messages"):
            return self.strategy.get_initial_messages(session, user_name=user_name)
        if hasattr(self.strategy, "get_initial_message"):
            msg = self.strategy.get_initial_message(session, user_name=user_name)
            return [msg] if isinstance(msg, str) else msg
        return ["こんにちは。"]

    def handle_user_turn(self, session, user_message: str) -> dict:
        result = self.strategy.process_turn(session, user_message)
        state = dict(session.state_data or {})
        state.update(result.get("state_updates") or {})
        session.state_data = state
        session.current_phase = result["next_phase"]
        session.save(update_fields=["state_data", "current_phase", "updated_at"])
        return result
