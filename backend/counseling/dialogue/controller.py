"""対話制御部。

states.TRANSITIONS に従って次に尋ねる要素を決め、質問文テンプレートから質問を提示する。
ユーザの回答は経験DB (Experience) に保存し、全発話と経験想起支援の呼び出しをログに残す。

セッションの状態は CounselingSession.state_data に次の形で保存する:
    {
        "state": 現在尋ねている要素 (states.py の状態キー),
        "failure_id": 失敗経験の Experience.id,
        "related_id": 想起中の関連経験の Experience.id (未作成なら None),
        "examples": 現在の質問に対してこれまでに提示した具体例のリスト,
    }
"""

from counseling.dialogue import recall_support, templates
from counseling.dialogue.states import (
    COMPLETED,
    EVALUATION,
    FAILURE_ACTION,
    FAILURE_POST_STATE,
    FAILURE_POST_THOUGHT,
    FAILURE_PRE_STATE,
    FAILURE_PRE_THOUGHT,
    INITIAL_STATE,
    PHASE_COMPLETED,
    PHASE_RELATED_RECALL,
    RELATED1_ACTION,
    RELATED1_POST_STATE,
    RELATED1_POST_THOUGHT,
    RELATED2_POST_STATE,
    RELATED2_PRE_STATE_ACTION,
    RERECALL_POST_STATE,
    RERECALL_PRE_STATE,
    STATES,
    TRANSITIONS,
    TYPE2_ENTRY,
)
from counseling.models import CounselingSession, Experience, Message, RecallSupportLog

YES = "はい"
NO = "いいえ"

RESPONSE_DISPLAY = {
    Message.RESPONSE_DONT_KNOW: "思いつかない",
    Message.RESPONSE_NOTHING: "特にない",
}

STATES_STARTING_RELATED_EXPERIENCE = (RELATED1_ACTION, RELATED2_PRE_STATE_ACTION)


class DialogueError(Exception):
    """ユーザの応答が現在の状態で受け付けられない場合に送出する。"""


class DialogueController:
    def __init__(self, session: CounselingSession):
        self.session = session
        self.data = dict(session.state_data or {})
        self._failure = None
        self._related = None

    # ------------------------------------------------------------------
    # 公開インタフェース
    # ------------------------------------------------------------------

    @classmethod
    def start(cls, session: CounselingSession, user_name: str) -> list[Message]:
        """セッションを開始し、挨拶と最初の質問を返す。"""
        failure = Experience.objects.create(session=session, kind=Experience.KIND_FAILURE)
        controller = cls(session)
        controller.data = {"state": INITIAL_STATE, "failure_id": failure.id, "related_id": None, "examples": []}
        controller.session.current_phase = STATES[INITIAL_STATE].phase

        messages = [
            controller._say(line, kind="greeting")
            for line in templates.question_lines("greeting", {"user_name": user_name})
        ]
        messages += controller._enter(INITIAL_STATE)
        controller._save()
        return messages

    @property
    def state(self) -> str:
        return self.data.get("state") or COMPLETED

    def input_state(self) -> dict:
        """フロントエンドが入力エリアを切り替えるための情報。"""
        state = STATES.get(self.state, STATES[COMPLETED])
        if state.key == COMPLETED:
            mode = "closed"
        elif state.yes_no:
            mode = "yes_no"
        else:
            mode = "free"
        return {
            "mode": mode,
            "state": state.key,
            "state_label": state.label,
            "phase": state.phase,
            "required": state.required,
        }

    def handle(self, response_type: str, content: str = "") -> tuple[Message, list[Message]]:
        """ユーザの応答を処理し、(ユーザ発話, エージェント発話のリスト) を返す。"""
        state = STATES.get(self.state)
        content = (content or "").strip()
        self._validate(state, response_type, content)

        user_message = self._record_user(response_type, RESPONSE_DISPLAY.get(response_type, content))

        if response_type == Message.RESPONSE_DONT_KNOW:
            agent_messages = [self._recall_support()]
        elif state.yes_no:
            agent_messages = self._handle_evaluation(content == YES)
        else:
            answered = response_type == Message.RESPONSE_ANSWER
            if answered:
                self._store(state.key, content)
            agent_messages = self._enter(TRANSITIONS[state.key]["answered" if answered else "skipped"])

        self._save()
        return user_message, agent_messages

    # ------------------------------------------------------------------
    # 3.1 共通処理: 要素を尋ねる
    # ------------------------------------------------------------------

    def _validate(self, state, response_type: str, content: str) -> None:
        if state is None or state.key == COMPLETED:
            raise DialogueError(templates.question_text("session_completed", {}))
        if response_type not in (Message.RESPONSE_ANSWER, Message.RESPONSE_DONT_KNOW, Message.RESPONSE_NOTHING):
            raise DialogueError(f"不明な応答種別です: {response_type}")
        if state.yes_no:
            if response_type != Message.RESPONSE_ANSWER or content not in (YES, NO):
                raise DialogueError("「はい」か「いいえ」で答えてください")
            return
        if response_type == Message.RESPONSE_NOTHING and state.required:
            raise DialogueError("この質問は省略できません")
        if response_type == Message.RESPONSE_ANSWER and not content:
            raise DialogueError("回答を入力してください")

    def _enter(self, next_state: str) -> list[Message]:
        """状態を遷移させ、その状態で提示する発話を返す。"""
        if next_state == TYPE2_ENTRY:
            # [種類2の想起] 1. 失敗経験の事後思想が得られていなければ失敗経験再想起フェーズへ
            next_state = RELATED2_PRE_STATE_ACTION if self.failure.post_thought else RERECALL_PRE_STATE

        self.data["state"] = next_state
        self.data["examples"] = []
        self.session.current_phase = STATES[next_state].phase
        if next_state in STATES_STARTING_RELATED_EXPERIENCE:
            # 新しい関連経験の想起を始める
            self.data["related_id"] = None
            self._related = None

        if next_state == COMPLETED:
            return self._present_origin()
        return [self._say(templates.question_text(next_state, self._variables()), kind="question")]

    def _recall_support(self) -> Message:
        """「思いつかない」: 経験想起支援機能で具体例を生成して提示し、同じ状態で応答を待つ。"""
        examples = list(self.data.get("examples") or [])
        result = recall_support.generate_example(self.state, self._variables(), examples)

        if result.output:
            message = self._say(result.output, kind="example")
            examples.append(result.output)
            self.data["examples"] = examples
        else:
            message = self._say(templates.question_text("recall_support_error", {}), kind="notice")

        RecallSupportLog.objects.create(
            session=self.session,
            message=message,
            phase=STATES[self.state].phase,
            element=self.state,
            attempt=len(examples) + (0 if result.output else 1),
            prompt=result.prompt,
            raw_output=result.raw_output,
            output=result.output,
            model=result.model,
            error=result.error,
        )
        return message

    # ------------------------------------------------------------------
    # 経験DB への保存
    # ------------------------------------------------------------------

    def _store(self, state: str, content: str) -> None:
        failure = self.failure
        if state == FAILURE_ACTION:
            failure.action = content
        elif state in (FAILURE_PRE_STATE, RERECALL_PRE_STATE):
            failure.pre_states = [*failure.pre_states, content]
        elif state in (FAILURE_POST_STATE, RERECALL_POST_STATE):
            # 再想起で得た事後状態は「失敗経験の事後状態」として追加し、以降の種類1の質問で使う
            failure.post_states = [*failure.post_states, content]
        elif state == FAILURE_PRE_THOUGHT:
            failure.pre_thought = content
        elif state == FAILURE_POST_THOUGHT:
            failure.post_thought = content
        elif state == RELATED1_ACTION:
            self._create_related(relation_type=1, action=content, pre_states=[self.current_failure_post_state])
            return
        elif state == RELATED2_PRE_STATE_ACTION:
            self._create_related(relation_type=2, pre_state_and_action=content, pre_thought=failure.post_thought)
            return
        elif state in (RELATED1_POST_STATE, RELATED2_POST_STATE):
            self.related.post_states = [*self.related.post_states, content]
            self.related.save()
            return
        elif state == RELATED1_POST_THOUGHT:
            self.related.post_thought = content
            self.related.save()
            return
        failure.save()

    def _create_related(self, relation_type: int, **fields) -> None:
        self._related = Experience.objects.create(
            session=self.session,
            kind=Experience.KIND_RELATED,
            relation_type=relation_type,
            **fields,
        )
        self.data["related_id"] = self._related.id

    # ------------------------------------------------------------------
    # 3.3 [評価] と起点の提示
    # ------------------------------------------------------------------

    def _handle_evaluation(self, positive: bool) -> list[Message]:
        self.related.evaluation = positive
        self.related.save()
        return self._enter(TRANSITIONS[EVALUATION]["yes" if positive else "no"])

    def _present_origin(self) -> list[Message]:
        key = "origin_type1" if self.related.relation_type == 1 else "origin_type2"
        variables = self._variables()
        origin = self._say(
            templates.question_text(key, variables), kind="origin", phase=PHASE_RELATED_RECALL, element=key
        )
        closing = self._say(templates.question_text("closing", variables), kind="closing", element="closing")
        return [origin, closing]

    # ------------------------------------------------------------------
    # 補助
    # ------------------------------------------------------------------

    @property
    def failure(self) -> Experience:
        if self._failure is None:
            self._failure = Experience.objects.get(id=self.data["failure_id"])
        return self._failure

    @property
    def related(self) -> Experience | None:
        if self._related is None and self.data.get("related_id"):
            self._related = Experience.objects.get(id=self.data["related_id"])
        return self._related

    @property
    def current_failure_post_state(self) -> str:
        """種類1の質問で使う失敗経験の事後状態 (再想起で追加されたものがあれば最新のもの)。"""
        post_states = self.failure.post_states
        return post_states[-1] if post_states else ""

    def _variables(self) -> dict[str, str]:
        """テンプレートに埋め込む変数。未回答の要素は空文字 (テンプレート側で「未回答」になる)。"""
        failure = self.failure
        related = self.related
        variables = {
            "failure_action": failure.action,
            "failure_pre_state": "／".join(failure.pre_states),
            "failure_post_state": "／".join(failure.post_states),
            "failure_pre_thought": failure.pre_thought,
            "failure_post_thought": failure.post_thought,
            "current_failure_post_state": self.current_failure_post_state,
            "related_action": "",
            "related_pre_state": "",
            "related_post_state": "",
            "related_pre_thought": "",
            "related_post_thought": "",
            "related_pre_state_and_action": "",
            "origin_failure_post_state": "",
        }
        if related is not None:
            variables.update(
                {
                    # 種類2では「事前状態と行動」の回答を関連経験の行動として質問文に埋め込む
                    "related_action": related.action or related.pre_state_and_action,
                    "related_pre_state": "／".join(related.pre_states),
                    "related_post_state": "／".join(related.post_states),
                    "related_pre_thought": related.pre_thought,
                    "related_post_thought": related.post_thought,
                    "related_pre_state_and_action": related.pre_state_and_action,
                    "origin_failure_post_state": related.pre_states[0] if related.pre_states else "",
                }
            )
        elif self.state == RELATED1_ACTION:
            variables["related_pre_state"] = self.current_failure_post_state
        elif self.state == RELATED2_PRE_STATE_ACTION:
            variables["related_pre_thought"] = failure.post_thought
        return variables

    def _say(self, text: str, kind: str, phase: str | None = None, element: str | None = None) -> Message:
        state = STATES[self.state]
        return Message.objects.create(
            session=self.session,
            sender=Message.SENDER_AGENT,
            content=text,
            phase=phase or state.phase,
            element=element if element is not None else state.key,
            kind=kind,
        )

    def _record_user(self, response_type: str, content: str) -> Message:
        state = STATES[self.state]
        return Message.objects.create(
            session=self.session,
            sender=Message.SENDER_USER,
            content=content,
            phase=state.phase,
            element=state.key,
            response_type=response_type,
        )

    def _save(self) -> None:
        self.session.state_data = self.data
        if self.state == COMPLETED:
            self.session.current_phase = PHASE_COMPLETED
        self.session.save(update_fields=["state_data", "current_phase", "updated_at"])
