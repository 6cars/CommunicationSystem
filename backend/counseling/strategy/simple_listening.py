from counseling.strategy.base import BaseDialogueStrategy


class SimpleListeningStrategy(BaseDialogueStrategy):
    """
    3つのフェーズ（失敗経験想起フェーズ、関連経験想起フェーズ、失敗経験再想起フェーズ）および評価・完了を管理する対話戦略。
    """

    # フェーズ定義
    PHASE_FAILURE_RECALL = "failure_recall"        # 失敗経験想起フェーズ
    PHASE_RELATED_RECALL = "related_recall"        # 関連経験想起フェーズ
    PHASE_FAILURE_RERECALL = "failure_rerecall"    # 失敗経験再想起フェーズ
    PHASE_COMPLETED = "completed"                  # セッション完了フェーズ

    # --- 失敗経験想起フェーズ内のステップ定義 ---
    STEP_ASK_PRE_SITUATION = "ask_pre_situation"     # 事前状態を尋ねるステップ（初期質問への回答待ち）
    STEP_ASK_POST_SITUATION = "ask_post_situation"   # 事後状態を尋ねるステップ（事前状態回答待ち）
    STEP_ASK_PRE_THOUGHT = "ask_pre_thought"         # 事前思想を尋ねるステップ（事後状態回答待ち）
    STEP_ASK_POST_THOUGHT = "ask_post_thought"       # 事後思想を尋ねるステップ（事前思想回答待ち）
    STEP_FINISH_FAILURE = "finish_failure"           # 失敗経験想起完了（互換用）

    # --- 関連経験想起フェーズ（状態一致）のステップ定義 ---
    STEP_REL_STATE_ASK_ACTION = "rel_state_ask_action"             # 関連経験の行動を尋ねるステップ（回答待ち）
    STEP_REL_STATE_ASK_POST_STATE = "rel_state_ask_post_state"     # 関連経験の事後状態を尋ねるステップ（回答待ち）

    # --- 関連経験想起フェーズ（思想一致）のステップ定義 ---
    STEP_REL_THOUGHT_ASK_PRE_STATE = "rel_thought_ask_pre_state"   # 関連経験の事前状態を尋ねるステップ（回答待ち）
    STEP_REL_THOUGHT_ASK_ACTION = "rel_thought_ask_action"         # 関連経験の行動を尋ねるステップ（回答待ち）
    STEP_REL_THOUGHT_ASK_POST_STATE = "rel_thought_ask_post_state" # 関連経験の事後状態を尋ねるステップ（回答待ち）

    # --- 関連経験の評価ステップ定義 ---
    STEP_REL_EVALUATION = "rel_evaluation"                         # 良い経験か尋ねるステップ（回答待ち）

    # --- 失敗経験再想起フェーズのステップ定義 ---
    STEP_RERECALL_ASK_STATES = "rerecall_ask_states"               # 別の事前/事後状態を尋ねるステップ（回答待ち）
    STEP_RERECALL_ASK_PRE_THOUGHT = "rerecall_ask_pre_thought"     # 別の事前思想を尋ねるステップ（回答待ち）
    STEP_RERECALL_ASK_POST_THOUGHT = "rerecall_ask_post_thought"   # 別の事後思想を尋ねるステップ（回答待ち）

    # =========================================================================
    # 判定および情報取得ヘルパー
    # =========================================================================

    @staticmethod
    def _is_negative_or_empty(text: str) -> bool:
        """ユーザーが『出ない』『思いつかない』『特にない』等の回答をしたか判定"""
        if not text:
            return True
        cleaned = text.strip().replace(" ", "").replace("　", "").replace("、", "").replace("。", "")
        if not cleaned:
            return True

        exact_negatives = {
            "ない", "ないです", "ありません", "特にない", "特になし", "特にありません", "ないかも",
            "思いつきません", "思いつきませんね", "思いつかないです", "思いつかない", "思いつきそうにない",
            "思い当たらない", "思い当たりません", "思い浮かびません", "思い浮かばない",
            "わからない", "わかりません", "分かりません", "分からん", "覚えてない", "覚えていません",
            "出ない", "出ません", "出てこない", "出てきません", "なし", "なしです",
            "特になにも", "何もない", "何もありません", "何もないです", "いいえ", "no", "none"
        }
        if cleaned in exact_negatives:
            return True

        # 40文字以下で想起不能・否定パターンの主要表現を含む場合
        if len(cleaned) <= 40:
            recall_failure_keywords = [
                "特にない", "特になし", "特にありません", "特に何",
                "思いつか", "思いつきま", "思い当た", "思い浮か", "浮かば",
                "覚えていな", "覚えてない", "覚えていま", "忘れて",
                "分からな", "わかりま", "分かりま", "わからな",
                "出ない", "出ません", "でてこ", "出てこ", "出てきま",
                "何もない", "何も思い", "何も浮か", "何もありま"
            ]
            for kw in recall_failure_keywords:
                if kw in cleaned:
                    return True

            # 単体で「ない」「ありません」「なし」で終わる短い文（例：「今のところない」「今はなし」など）
            if cleaned.endswith("ない") or cleaned.endswith("ないです") or cleaned.endswith("ありません") or cleaned.endswith("なし"):
                if not (cleaned.endswith("いけない") or cleaned.endswith("いけません") or cleaned.endswith("ならない") or cleaned.endswith("なりません")):
                    return True

        return False

    @staticmethod
    def _is_positive_evaluation(text: str) -> bool:
        """評価ステップで『良い経験だと感じられるか』の回答を判定"""
        if not text:
            return False
        cleaned = text.strip().replace(" ", "").replace("　", "").replace("、", "").replace("。", "")

        # 明確な否定パターン
        negative_words = [
            "良くない", "よくない", "思えない", "感じられない", "悪い", "後悔",
            "いいえ", "思わない", "感じない", "嫌", "微妙", "そうは思えない", "そうは思わない", "ダメ"
        ]
        for nw in negative_words:
            if nw in cleaned:
                return False

        # 肯定パターン
        positive_words = [
            "良い", "よい", "いい", "感じられる", "感じます", "思える", "思えます",
            "はい", "プラス", "学び", "よかった", "良かった", "感謝", "成長", "糧", "有益"
        ]
        for pw in positive_words:
            if pw in cleaned:
                return True

        # 特に否定語が含まれずポジティブ寄りの回答ならTrueとする
        return True

    @staticmethod
    def _get_failure_action(history: dict) -> str:
        return history.get("failure_and_action") or history.get("failure_action") or "失敗したときの行動"

    @staticmethod
    def _get_failure_pre_state(history: dict) -> str:
        return history.get("pre_situation") or history.get("failure_pre_state") or "当時の状況"

    @staticmethod
    def _get_failure_post_state(history: dict) -> str:
        return history.get("post_situation") or history.get("failure_post_state") or "その結果の状態"

    @staticmethod
    def _get_failure_post_thought(history: dict) -> str:
        return history.get("post_thought") or history.get("failure_post_thought") or ""

    def _has_failure_post_thought(self, history: dict) -> bool:
        thought = self._get_failure_post_thought(history)
        return bool(thought and not self._is_negative_or_empty(thought))

    # =========================================================================
    # メイン処理
    # =========================================================================

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
        elif current_phase == self.PHASE_COMPLETED:
            return self._handle_completed(step, user_message, state_data, history)
        else:
            return self._handle_failure_recall(step, user_message, state_data, history)

    # =========================================================================
    # 1. 失敗経験想起フェーズ
    # =========================================================================

    def _handle_failure_recall(self, step: str | None, user_message: str, state_data: dict, history: dict) -> dict:
        turn_count = int(state_data.get("turn_count", 0)) + 1

        # ステップ 1: 初期質問への回答を受信 -> 事前状態を尋ねる
        if not step or step == "ask_failure" or step == self.STEP_ASK_PRE_SITUATION:
            history["failure_and_action"] = user_message
            history["failure_action"] = user_message
            reply_texts = [
                "その行動をとる直前、まわりの状況やメンバーの様子はどのような状態でしたか？"
            ]
            next_step = self.STEP_ASK_POST_SITUATION
            next_phase = self.PHASE_FAILURE_RECALL

        # ステップ 2: 事前状態についての回答を受信 -> 事後状態を尋ねる
        elif step == self.STEP_ASK_POST_SITUATION:
            history["pre_situation"] = user_message
            history["failure_pre_state"] = user_message
            reply_texts = [
                "その行動をとった後、まわりの状況やメンバーの反応はどのような状態になってしまいましたか？"
            ]
            next_step = self.STEP_ASK_PRE_THOUGHT
            next_phase = self.PHASE_FAILURE_RECALL

        # ステップ 3: 事後状態についての回答を受信 -> 事前思想を尋ねる
        elif step == self.STEP_ASK_PRE_THOUGHT:
            history["post_situation"] = user_message
            history["failure_post_state"] = user_message
            reply_texts = [
                "その行動を起こす前、あなた自身の頭の中ではどのようなことを考えていましたか？"
            ]
            next_step = self.STEP_ASK_POST_THOUGHT
            next_phase = self.PHASE_FAILURE_RECALL

        # ステップ 4: 事前思想についての回答を受信 -> 事後思想を尋ねる
        elif step == self.STEP_ASK_POST_THOUGHT:
            history["pre_thought"] = user_message
            history["failure_pre_thought"] = user_message
            reply_texts = [
                "その結果になったことで、あなた自身はどのようなことに気づいたり、何を学んだりしましたか？"
            ]
            next_step = self.STEP_FINISH_FAILURE
            next_phase = self.PHASE_FAILURE_RECALL

        # ステップ 5: 事後思想についての回答を受信 -> 関連経験想起フェーズ（状態一致）へ移行
        else:
            history["post_thought"] = user_message
            history["failure_post_thought"] = user_message

            failure_post_state = self._get_failure_post_state(history)
            reply_texts = [
                "お話しいただきありがとうございます。失敗した経験について振り返ることができましたね。",
                "それでは、次のステップである『関連経験想起フェーズ』に進みましょう。",
                f"先ほどお話しいただいた「{failure_post_state}」になったとき，どのような行動をとりましたか？"
            ]
            next_step = self.STEP_REL_STATE_ASK_ACTION
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

    # =========================================================================
    # 2. 関連経験想起フェーズ（状態一致・思想一致・評価）
    # =========================================================================

    def _handle_related_recall(self, step: str | None, user_message: str, state_data: dict, history: dict) -> dict:
        turn_count = int(state_data.get("turn_count", 0)) + 1
        failure_post_state = self._get_failure_post_state(history)
        failure_action = self._get_failure_action(history)
        failure_post_thought = self._get_failure_post_thought(history)
        has_post_thought = self._has_failure_post_thought(history)

        # ---------------------------------------------------------------------
        # ルートA: 状態一致の関連経験想起
        # ---------------------------------------------------------------------

        # ステップ A-1: 関連経験の行動を尋ねる（回答待ち）
        if not step or step == "initial" or step == self.STEP_REL_STATE_ASK_ACTION:
            is_empty = self._is_negative_or_empty(user_message)
            if is_empty:
                # 出ないなら（かつ失敗経験の事後思想があるなら）思想一致の関連経験想起に進む
                if has_post_thought:
                    reply_texts = [
                        "その状況での具体的な行動は思い当たらなくても大丈夫です。",
                        f"「失敗から得た『{failure_post_thought}』という学びを心に留めていたとき，まわりの状況や様子はどのような状態でしたか？」"
                    ]
                    next_step = self.STEP_REL_THOUGHT_ASK_PRE_STATE
                    next_phase = self.PHASE_RELATED_RECALL
                # 出ないなら（かつ失敗経験の事後思想がないなら）失敗経験再想起フェーズに進む
                else:
                    reply_texts = [
                        "思い当たらなくても大丈夫です。焦らず進めましょう。",
                        "それでは、先ほどの失敗経験について、別の視点から捉え直してみましょう。",
                        f"「『{failure_action}』という行動をとったとき，まわりの状況や様子について，これまでとは違う別の視点や別の変化は思い当たりませんか？」"
                    ]
                    next_step = self.STEP_RERECALL_ASK_STATES
                    next_phase = self.PHASE_FAILURE_RERECALL
            else:
                # 出たなら関連経験の事後状態を尋ねる
                history["rel_action"] = user_message
                history["rel_pre_state"] = failure_post_state
                reply_texts = [
                    f"『{user_message}』という行動をとったあと，まわりの状況やメンバーの様子はどのような状態になりましたか？"
                ]
                next_step = self.STEP_REL_STATE_ASK_POST_STATE
                next_phase = self.PHASE_RELATED_RECALL

        # ステップ A-2: 関連経験の事後状態を尋ねる（回答待ち）
        elif step == self.STEP_REL_STATE_ASK_POST_STATE:
            is_empty = self._is_negative_or_empty(user_message)
            if is_empty:
                # 出ないなら（かつ失敗経験の事後思想があるなら）思想一致の関連経験想起に進む
                if has_post_thought:
                    reply_texts = [
                        "その後の状況について思い当たることはなかったのですね。大丈夫です。",
                        f"「失敗から得た『{failure_post_thought}』という学びを心に留めていたとき，まわりの状況や様子はどのような状態でしたか？」"
                    ]
                    next_step = self.STEP_REL_THOUGHT_ASK_PRE_STATE
                    next_phase = self.PHASE_RELATED_RECALL
                # 出ないなら（かつ失敗経験の事後思想がないなら）失敗経験再想起フェーズに進む
                else:
                    reply_texts = [
                        "その後の状況について思い当たらなくても大丈夫です。",
                        "それでは、先ほどの失敗経験について、別の視点から捉え直してみましょう。",
                        f"「『{failure_action}』という行動をとったとき，まわりの状況や様子について，これまでとは違う別の視点や別の変化は思い当たりませんか？」"
                    ]
                    next_step = self.STEP_RERECALL_ASK_STATES
                    next_phase = self.PHASE_FAILURE_RERECALL
            else:
                # 出たなら評価に進む
                history["rel_post_state"] = user_message
                reply_texts = [
                    "「今のエピソードを振り返ってみて，失敗した経験はあなたにとって良い経験だと感じられますか？」"
                ]
                next_step = self.STEP_REL_EVALUATION
                next_phase = self.PHASE_RELATED_RECALL

        # ---------------------------------------------------------------------
        # ルートB: 思想一致の関連経験想起
        # ---------------------------------------------------------------------

        # ステップ B-1: 関連経験の事前状態を尋ねる（回答待ち）
        elif step == self.STEP_REL_THOUGHT_ASK_PRE_STATE:
            is_empty = self._is_negative_or_empty(user_message)
            if is_empty:
                # 出ないなら失敗経験再想起フェーズに進む
                reply_texts = [
                    "思い当たらなくても大丈夫ですよ。",
                    "それでは、先ほどの失敗経験について、別の視点から捉え直してみましょう。",
                    f"「『{failure_action}』という行動をとったとき，まわりの状況や様子について，これまでとは違う別の視点や別の変化は思い当たりませんか？」"
                ]
                next_step = self.STEP_RERECALL_ASK_STATES
                next_phase = self.PHASE_FAILURE_RERECALL
            else:
                # 出たなら関連経験の行動を尋ねる
                history["rel_pre_state"] = user_message
                history["rel_pre_thought"] = failure_post_thought
                reply_texts = [
                    f"「『{user_message}』という状況の中で，その学びを活かしてどのような行動をとりましたか？」"
                ]
                next_step = self.STEP_REL_THOUGHT_ASK_ACTION
                next_phase = self.PHASE_RELATED_RECALL

        # ステップ B-2: 関連経験の行動を尋ねる（回答待ち）
        elif step == self.STEP_REL_THOUGHT_ASK_ACTION:
            is_empty = self._is_negative_or_empty(user_message)
            if is_empty:
                # 出ないなら失敗経験再想起フェーズに進む
                reply_texts = [
                    "そのときの行動について思い当たらなくても大丈夫です。",
                    "それでは、先ほどの失敗経験について、別の視点から捉え直してみましょう。",
                    f"「『{failure_action}』という行動をとったとき，まわりの状況や様子について，これまでとは違う別の視点や別の変化は思い当たりませんか？」"
                ]
                next_step = self.STEP_RERECALL_ASK_STATES
                next_phase = self.PHASE_FAILURE_RERECALL
            else:
                # 出たなら関連経験の事後状態を尋ねる
                history["rel_action"] = user_message
                reply_texts = [
                    f"「『{user_message}』という行動をとったあと，まわりの状況や様子はどのような状態になりましたか？」"
                ]
                next_step = self.STEP_REL_THOUGHT_ASK_POST_STATE
                next_phase = self.PHASE_RELATED_RECALL

        # ステップ B-3: 関連経験の事後状態を尋ねる（回答待ち）
        elif step == self.STEP_REL_THOUGHT_ASK_POST_STATE:
            is_empty = self._is_negative_or_empty(user_message)
            if is_empty:
                # 出ないなら失敗経験再想起フェーズに進む
                reply_texts = [
                    "その後の状況について思い当たらなくても大丈夫です。",
                    "それでは、先ほどの失敗経験について、別の視点から捉え直してみましょう。",
                    f"「『{failure_action}』という行動をとったとき，まわりの状況や様子について，これまでとは違う別の視点や別の変化は思い当たりませんか？」"
                ]
                next_step = self.STEP_RERECALL_ASK_STATES
                next_phase = self.PHASE_FAILURE_RERECALL
            else:
                # 出たなら評価に進む
                history["rel_post_state"] = user_message
                reply_texts = [
                    "「今のエピソードを振り返ってみて，失敗した経験はあなたにとって良い経験だと感じられますか？」"
                ]
                next_step = self.STEP_REL_EVALUATION
                next_phase = self.PHASE_RELATED_RECALL

        # ---------------------------------------------------------------------
        # 評価: 関連経験の評価
        # ---------------------------------------------------------------------
        elif step == self.STEP_REL_EVALUATION:
            is_positive = self._is_positive_evaluation(user_message)
            history["rel_evaluation"] = user_message

            if not is_positive:
                # 良くないなら関連経験想起フェーズのスタート地点へ行く
                reply_texts = [
                    "率直なお気持ちをお聞かせいただきありがとうございます。無理に良い経験と捉える必要はありません。",
                    "もう一度別の視点から、関連する経験を振り返ってみましょう。",
                    f"先ほどお話しいただいた「{failure_post_state}」になったとき，どのような行動をとりましたか？"
                ]
                next_step = self.STEP_REL_STATE_ASK_ACTION
                next_phase = self.PHASE_RELATED_RECALL
            else:
                # 良ければ失敗経験と肯定的な関連経験をつなげたフィードバックを返す
                rel_action = history.get("rel_action", "その後の行動")
                rel_post_state = history.get("rel_post_state", "良い状態")

                thought_part = f"『{failure_post_thought}』という気づきを得て、" if has_post_thought else ""
                feedback_text = (
                    f"『{failure_action}』という出来事から{thought_part}"
                    f"『{rel_action}』という行動を起こし、"
                    f"『{rel_post_state}』という状況へと繋げることができたのですね。"
                )

                reply_texts = [
                    "そう感じていただけて本当によかったです！",
                    feedback_text,
                    "失敗した経験をそのままにせず、その後の状況を好転させる糧として活かすことができたのは、あなたにとってかけがえのない素晴らしい経験です。お話しいただき本当にありがとうございました！"
                ]
                next_step = "completed"
                next_phase = self.PHASE_COMPLETED

        else:
            # 想定外のステップの場合はスタート地点へフォールバック
            reply_texts = [
                f"先ほどお話しいただいた「{failure_post_state}」になったとき，どのような行動をとりましたか？"
            ]
            next_step = self.STEP_REL_STATE_ASK_ACTION
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
                "engine": "related_recall_strategy",
            },
        }

    # =========================================================================
    # 3. 失敗経験再想起フェーズ
    # =========================================================================

    def _handle_failure_rerecall(self, step: str | None, user_message: str, state_data: dict, history: dict) -> dict:
        turn_count = int(state_data.get("turn_count", 0)) + 1
        failure_action = self._get_failure_action(history)
        failure_pre_state = self._get_failure_pre_state(history)
        failure_post_state = self._get_failure_post_state(history)

        # ステップ 1: 別の事前状態，事後状態の回答を受信 -> 別の事前思想を尋ねる
        if not step or step == self.STEP_RERECALL_ASK_STATES:
            history["re_failure_states"] = user_message
            reply_texts = [
                f"「『{failure_pre_state}』という状況で『{failure_action}』という行動をとった当時，別の意図や，違った気持ち・考え方で動いていたということはありませんか？」"
            ]
            next_step = self.STEP_RERECALL_ASK_PRE_THOUGHT
            next_phase = self.PHASE_FAILURE_RERECALL

        # ステップ 2: 別の事前思想の回答を受信（出ないなら次に進む／出ても出なくても次へ） -> 別の事後思想を尋ねる
        elif step == self.STEP_RERECALL_ASK_PRE_THOUGHT:
            history["re_failure_pre_thought"] = user_message
            reply_texts = [
                "「その結果生じた状況から，先ほどとは異なる視点で，何か別の気づきや教訓を得られたりはしませんか？」"
            ]
            next_step = self.STEP_RERECALL_ASK_POST_THOUGHT
            next_phase = self.PHASE_FAILURE_RERECALL

        # ステップ 3: 別の事後思想の回答を受信（出ても出てなくでも関連経験想起フェーズに進む）
        else:
            history["re_failure_post_thought"] = user_message
            # 新たな事後思想が出た場合は、以後の思想一致関連経験想起でも活用できるよう更新
            if not self._is_negative_or_empty(user_message):
                history["post_thought"] = user_message
                history["failure_post_thought"] = user_message

            reply_texts = [
                "新たな視点から失敗経験を見つめ直すことができましたね。",
                "それでは、改めて関連経験想起フェーズに進みましょう。",
                f"先ほどお話しいただいた「{failure_post_state}」になったとき，どのような行動をとりましたか？"
            ]
            next_step = self.STEP_REL_STATE_ASK_ACTION
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
                "engine": "failure_rerecall_strategy",
            },
        }

    # =========================================================================
    # 4. セッション完了後の対応
    # =========================================================================

    def _handle_completed(self, step: str | None, user_message: str, state_data: dict, history: dict) -> dict:
        turn_count = int(state_data.get("turn_count", 0)) + 1
        reply_texts = [
            "対話セッションは完了しています。振り返りいただきありがとうございました！",
            "新しいセッションを開始したい場合は、管理者画面またはログイン画面から再度始めてください。"
        ]
        return {
            "reply_text": "\n\n".join(reply_texts),
            "reply_texts": reply_texts,
            "next_phase": self.PHASE_COMPLETED,
            "state_updates": {
                "turn_count": turn_count,
                "step": "completed",
                "history": history,
            },
            "strategy_metadata": {
                "phase": self.PHASE_COMPLETED,
                "step": "completed",
                "engine": "completed_strategy",
            },
        }
