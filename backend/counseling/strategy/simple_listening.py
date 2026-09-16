from counseling.strategy.base import BaseDialogueStrategy


class SimpleListeningStrategy(BaseDialogueStrategy):
    """
    3つのフェーズ（失敗経験想起フェーズ、関連経験想起フェーズ、失敗経験再想起フェーズ）を管理する対話戦略。
    まずは「失敗経験想起フェーズ」の対話フローを実装。
    """

    # フェーズ定義
    PHASE_FAILURE_RECALL = "failure_recall"        # 失敗経験想起フェーズ
    PHASE_RELATED_RECALL = "related_recall"        # 関連経験想起フェーズ
    PHASE_FAILURE_RERECALL = "failure_rerecall"    # 失敗経験再想起フェーズ

    # 失敗経験想起フェーズ内のステップ定義
    STEP_ASK_PRE_SITUATION = "ask_pre_situation"     # 事前状態を尋ねるステップ（初期回答待ち）
    STEP_ASK_POST_SITUATION = "ask_post_situation"   # 事後状態を尋ねるステップ（事前状態回答待ち）
    STEP_ASK_PRE_THOUGHT = "ask_pre_thought"         # 事前思想を尋ねるステップ（事後状態回答待ち）
    STEP_ASK_POST_THOUGHT = "ask_post_thought"       # 事後思想を尋ねるステップ（事前思想回答待ち）
    STEP_FINISH_FAILURE = "finish_failure"           # 失敗経験想起完了 -> 関連経験想起へ（事後思想回答待ち）

    def process_turn(self, session, user_message: str) -> dict:
        current_phase = session.current_phase or self.PHASE_FAILURE_RECALL
        state_data = dict(session.state_data or {})
        step = state_data.get("step")
        history = dict(state_data.get("history") or {})

        # 初期フェーズ（initial）の場合は failure_recall として扱う
        if current_phase == "initial":
            current_phase = self.PHASE_FAILURE_RECALL

        # フェーズごとのハンドラ呼び出し
        if current_phase == self.PHASE_FAILURE_RECALL:
            return self._handle_failure_recall(step, user_message, state_data, history)
        elif current_phase == self.PHASE_RELATED_RECALL:
            return self._handle_related_recall(step, user_message, state_data, history)
        elif current_phase == self.PHASE_FAILURE_RERECALL:
            return self._handle_failure_rerecall(step, user_message, state_data, history)
        else:
            return self._handle_failure_recall(step, user_message, state_data, history)

    def _handle_failure_recall(self, step: str | None, user_message: str, state_data: dict, history: dict) -> dict:
        """
        失敗経験想起フェーズの対話フロー:
        初期メッセージ（3通）:
          1. 挨拶
          2. 安心して話してほしい旨
          3. 「あなたは、失敗した時どのような行動をとってしまいましたか？」

        対話ターン:
        1. ユーザーが失敗経験・行動を入力
           -> 失敗経験の事前状態を尋ねる:
              「その行動をとる直前、まわりの状況やメンバーの様子はどのような状態でしたか？」
        2. ユーザーが事前状態を入力
           -> 失敗経験の事後状態を尋ねる:
              「その行動をとった後、まわりの状況やメンバーの反応はどのような状態になってしまいましたか？」
        3. ユーザーが事後状態を入力
           -> 失敗経験の事前思想を尋ねる（出ないなら次に進む）:
              「その行動を起こす前、あなた自身の頭の中ではどのようなことを考えていましたか？」
        4. ユーザーが事前思想を入力（出ても出なくても）
           -> 失敗経験の事後思想を尋ねる（でても出なくても関連経験想起フェーズに進む）:
              「その結果になったことで、あなた自身はどのようなことに気づいたり、何を学んだりしましたか？」
        5. ユーザーが事後思想を入力（出ても出なくても）
           -> 関連経験想起フェーズへ進む
        """
        turn_count = int(state_data.get("turn_count", 0)) + 1

        # ステップ 1: 初期質問（初期4通）への回答を受信
        # -> 事前状態を尋ねる
        if not step or step == "ask_failure" or step == self.STEP_ASK_PRE_SITUATION:
            history["failure_and_action"] = user_message
            reply_texts = [
                "その行動をとる直前、まわりの状況やメンバーの様子はどのような状態でしたか？"
            ]
            next_step = self.STEP_ASK_POST_SITUATION
            next_phase = self.PHASE_FAILURE_RECALL

        # ステップ 2: 事前状態についての回答を受信
        # -> 事後状態を尋ねる
        elif step == self.STEP_ASK_POST_SITUATION:
            history["pre_situation"] = user_message
            reply_texts = [
                "その行動をとった後、まわりの状況やメンバーの反応はどのような状態になってしまいましたか？"
            ]
            next_step = self.STEP_ASK_PRE_THOUGHT
            next_phase = self.PHASE_FAILURE_RECALL

        # ステップ 3: 事後状態についての回答を受信
        # -> 事前思想を尋ねる（出ないなら次に進む）
        elif step == self.STEP_ASK_PRE_THOUGHT:
            history["post_situation"] = user_message
            reply_texts = [
                "その行動を起こす前、あなた自身の頭の中ではどのようなことを考えていましたか？"
            ]
            next_step = self.STEP_ASK_POST_THOUGHT
            next_phase = self.PHASE_FAILURE_RECALL

        # ステップ 4: 事前思想についての回答を受信（出ても出なくても）
        # -> 事後思想を尋ねる（でても出なくても関連経験想起フェーズに進む）
        elif step == self.STEP_ASK_POST_THOUGHT:
            history["pre_thought"] = user_message
            reply_texts = [
                "その結果になったことで、あなた自身はどのようなことに気づいたり、何を学んだりしましたか？"
            ]
            next_step = self.STEP_FINISH_FAILURE
            next_phase = self.PHASE_FAILURE_RECALL

        # ステップ 5: 事後思想についての回答を受信（でても出なくても）
        # -> 失敗経験想起フェーズを完了し、関連経験想起フェーズへ進む
        else:
            history["post_thought"] = user_message
            reply_texts = [
                "お話しいただきありがとうございます。失敗した経験について振り返ることができましたね。",
                "それでは、次のステップである『関連経験想起フェーズ』に進みましょう。"
            ]
            next_step = "initial"
            next_phase = self.PHASE_RELATED_RECALL

        return {
            "reply_text": "\n\n".join(reply_texts),
            "reply_texts": reply_texts,
            "next_phase": next_phase,
            "state_updates": {
                "turn_count": turn_count,
                "step": next_step,
                "history": history,
            },
            "strategy_metadata": {
                "phase": next_phase,
                "step": next_step,
                "engine": "failure_recall_strategy",
            },
        }

    def _handle_related_recall(self, step: str | None, user_message: str, state_data: dict, history: dict) -> dict:
        """関連経験想起フェーズ（今後実装予定）"""
        turn_count = int(state_data.get("turn_count", 0)) + 1
        return {
            "reply_text": "【関連経験想起フェーズ（準備中）】\nこのフェーズの具体的な対話フローは今後実装予定です。",
            "reply_texts": ["【関連経験想起フェーズ（準備中）】\nこのフェーズの具体的な対話フローは今後実装予定です。"],
            "next_phase": self.PHASE_RELATED_RECALL,
            "state_updates": {
                "turn_count": turn_count,
                "step": "in_progress",
            },
            "strategy_metadata": {
                "phase": self.PHASE_RELATED_RECALL,
                "engine": "related_recall_strategy",
            },
        }

    def _handle_failure_rerecall(self, step: str | None, user_message: str, state_data: dict, history: dict) -> dict:
        """失敗経験再想起フェーズ（今後実装予定）"""
        turn_count = int(state_data.get("turn_count", 0)) + 1
        return {
            "reply_text": "【失敗経験再想起フェーズ（準備中）】\nこのフェーズの具体的な対話フローは今後実装予定です。",
            "reply_texts": ["【失敗経験再想起フェーズ（準備中）】\nこのフェーズの具体的な対話フローは今後実装予定です。"],
            "next_phase": self.PHASE_FAILURE_RERECALL,
            "state_updates": {
                "turn_count": turn_count,
                "step": "in_progress",
            },
            "strategy_metadata": {
                "phase": self.PHASE_FAILURE_RERECALL,
                "engine": "failure_rerecall_strategy",
            },
        }
