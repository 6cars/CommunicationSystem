from counseling.strategy.base import BaseDialogueStrategy


class SimpleListeningStrategy(BaseDialogueStrategy):
    """ルールベースの傾聴戦略。将来 LLM / 強化学習実装に差し替え可能。"""

    FATIGUE_KEYWORDS = ("疲れ", "つかれ", "しんど", "眠い", "残業", "忙しい")
    ANXIETY_KEYWORDS = ("不安", "心配", "怖い", "緊張", "焦")
    SADNESS_KEYWORDS = ("悲しい", "つらい", "辛い", "落ち込", "孤独")

    def process_turn(self, session, user_message: str) -> dict:
        intent = self._detect_intent(user_message)
        next_phase = self._next_phase(session.current_phase, intent)
        reply_text = self._compose_reply(user_message, intent, next_phase)
        turn_count = int((session.state_data or {}).get("turn_count", 0)) + 1

        return {
            "reply_text": reply_text,
            "next_phase": next_phase,
            "state_updates": {
                "turn_count": turn_count,
                "last_intent": intent,
            },
            "strategy_metadata": {
                "phase": next_phase,
                "intent": intent,
                "engine": "simple_listening",
            },
        }

    def _detect_intent(self, text: str) -> str:
        if any(word in text for word in self.FATIGUE_KEYWORDS):
            return "expression_of_fatigue"
        if any(word in text for word in self.ANXIETY_KEYWORDS):
            return "expression_of_anxiety"
        if any(word in text for word in self.SADNESS_KEYWORDS):
            return "expression_of_sadness"
        return "open_sharing"

    def _next_phase(self, current_phase: str, intent: str) -> str:
        if current_phase == "initial":
            return "active_listening"
        if intent != "open_sharing":
            return "exploring"
        return current_phase if current_phase != "initial" else "active_listening"

    def _compose_reply(self, user_message: str, intent: str, phase: str) -> str:
        return "あ"
