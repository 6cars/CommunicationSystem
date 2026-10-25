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

ログを取らないモード (CounselingSession.LOG_MODE_ANONYMOUS) では、ユーザの回答と具体例をサーバに保存しない。
- 経験DB には書き込まず、経験と具体例は private_state としてクライアントに返す。
  クライアントは次の応答と一緒に private_state を送り返し、サーバはそれを使って質問文を組み立てる。
- 発話ログには、エージェントの質問文の回答部分を伏せ字 (※) にしたものだけを残す。
  ユーザの自由記述の回答と具体例は ※ に置き換え、経験想起支援の呼び出しログ (プロンプト・出力) は残さない。
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

# private_state でやり取りする経験の項目
PRIVATE_TEXT_FIELDS = ("action", "pre_thought", "post_thought", "pre_state_and_action")
PRIVATE_LIST_FIELDS = ("pre_states", "post_states")


class DialogueError(Exception):
    """ユーザの応答が現在の状態で受け付けられない場合に送出する。"""


class DialogueController:
    def __init__(self, session: CounselingSession, private_state: dict | None = None):
        self.session = session
        self.data = dict(session.state_data or {})
        self.anonymous = session.log_mode == CounselingSession.LOG_MODE_ANONYMOUS
        self.private = private_state if isinstance(private_state, dict) else {}
        self._failure = None
        self._related = None

    # ------------------------------------------------------------------
    # 公開インタフェース
    # ------------------------------------------------------------------

    @classmethod
    def start(cls, session: CounselingSession, user_name: str) -> tuple["DialogueController", list[Message]]:
        """セッションを開始し、(コントローラ, 挨拶と最初の質問) を返す。"""
        controller = cls(session)
        if controller.anonymous:
            controller._failure = Experience(session=session, kind=Experience.KIND_FAILURE)
            failure_id = None
        else:
            failure_id = Experience.objects.create(session=session, kind=Experience.KIND_FAILURE).id
        controller.data = {"state": INITIAL_STATE, "failure_id": failure_id, "related_id": None, "examples": []}
        controller.session.current_phase = STATES[INITIAL_STATE].phase

        variables = {"user_name": user_name}
        messages = [
            controller._say(line, kind="greeting", masked=masked)
            for line, masked in zip(
                templates.question_lines("greeting", variables),
                templates.question_lines("greeting", templates.mask(variables)),
            )
        ]
        messages += controller._enter(INITIAL_STATE)
        controller._save()
        return controller, messages

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

    def private_state(self) -> dict | None:
        """ログを取らないモードで、クライアントに預ける経験と具体例。ログを取るモードでは None。"""
        if not self.anonymous:
            return None
        return {
            "failure": _experience_to_private(self.failure),
            "related": _experience_to_private(self.related) if self.related else None,
            "examples": self._examples(),
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
        self._set_examples([])
        self.session.current_phase = STATES[next_state].phase
        if next_state in STATES_STARTING_RELATED_EXPERIENCE:
            # 新しい関連経験の想起を始める
            self.data["related_id"] = None
            self.private["related"] = None
            self._related = None

        if next_state == COMPLETED:
            return self._present_origin()
        return [self._say_template(next_state, kind="question")]

    def _recall_support(self) -> Message:
        """「思いつかない」: 経験想起支援機能で具体例を生成して提示し、同じ状態で応答を待つ。"""
        examples = self._examples()
        result = recall_support.generate_example(self.state, self._variables(), examples)

        if result.output:
            message = self._say(result.output, kind="example")
            examples.append(result.output)
            self._set_examples(examples)
        else:
            message = self._say_template("recall_support_error", kind="notice")

        if self.anonymous:
            # プロンプトにも出力にもユーザの回答や具体例が含まれるので残さない
            return message
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
            self._persist(self.related)
            return
        elif state == RELATED1_POST_THOUGHT:
            self.related.post_thought = content
            self._persist(self.related)
            return
        self._persist(failure)

    def _create_related(self, relation_type: int, **fields) -> None:
        self._related = Experience(
            session=self.session,
            kind=Experience.KIND_RELATED,
            relation_type=relation_type,
            **fields,
        )
        self._persist(self._related)
        self.data["related_id"] = self._related.id

    def _persist(self, experience: Experience) -> None:
        """ログを取らないモードでは経験DBに書き込まない。"""
        if not self.anonymous:
            experience.save()

    # ------------------------------------------------------------------
    # 3.3 [評価] と起点の提示
    # ------------------------------------------------------------------

    def _handle_evaluation(self, positive: bool) -> list[Message]:
        self.related.evaluation = positive
        self._persist(self.related)
        return self._enter(TRANSITIONS[EVALUATION]["yes" if positive else "no"])

    def _present_origin(self) -> list[Message]:
        key = "origin_type1" if self.related.relation_type == 1 else "origin_type2"
        origin = self._say_template(key, kind="origin", phase=PHASE_RELATED_RECALL, element=key)
        closing = self._say_template("closing", kind="closing", element="closing")
        return [origin, closing]

    # ------------------------------------------------------------------
    # 補助
    # ------------------------------------------------------------------

    @property
    def failure(self) -> Experience:
        if self._failure is None:
            if self.anonymous:
                self._failure = self._experience_from_private("failure", Experience.KIND_FAILURE)
            else:
                self._failure = Experience.objects.get(id=self.data["failure_id"])
        return self._failure

    @property
    def related(self) -> Experience | None:
        if self._related is None:
            if self.anonymous:
                if isinstance(self.private.get("related"), dict):
                    self._related = self._experience_from_private("related", Experience.KIND_RELATED)
            elif self.data.get("related_id"):
                self._related = Experience.objects.get(id=self.data["related_id"])
        return self._related

    def _experience_from_private(self, key: str, kind: str) -> Experience:
        """クライアントから送り返された private_state の経験を、保存しない Experience にする。"""
        raw = self.private.get(key)
        raw = raw if isinstance(raw, dict) else {}
        fields = {name: str(raw.get(name) or "") for name in PRIVATE_TEXT_FIELDS}
        for name in PRIVATE_LIST_FIELDS:
            values = raw.get(name)
            fields[name] = [str(v) for v in values] if isinstance(values, list) else []
        if kind == Experience.KIND_RELATED:
            fields["relation_type"] = 2 if raw.get("relation_type") == 2 else 1
            fields["evaluation"] = raw.get("evaluation") if isinstance(raw.get("evaluation"), bool) else None
        return Experience(session=self.session, kind=kind, **fields)

    def _examples(self) -> list[str]:
        source = self.private if self.anonymous else self.data
        examples = source.get("examples")
        return [str(e) for e in examples] if isinstance(examples, list) else []

    def _set_examples(self, examples: list[str]) -> None:
        if self.anonymous:
            self.private["examples"] = examples
            self.data["examples"] = []
        else:
            self.data["examples"] = examples

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

    def _say_template(self, key: str, kind: str, **kwargs) -> Message:
        """質問文テンプレートから発話する。ログを取らないモードでは、回答を埋め込んだ部分を伏せ字にしてログに残す。"""
        variables = self._variables()
        return self._say(
            templates.question_text(key, variables),
            kind=kind,
            masked=templates.question_text(key, templates.mask(variables)),
            **kwargs,
        )

    def _say(
        self,
        text: str,
        kind: str,
        phase: str | None = None,
        element: str | None = None,
        masked: str = templates.MASK,
    ) -> Message:
        """エージェントの発話を記録する。ログを取らないモードでは text の代わりに masked を保存する
        (省略時は発話全体を伏せ字にする)。返す Message の content は常に text (クライアントに表示する文)。"""
        state = STATES[self.state]
        message = Message.objects.create(
            session=self.session,
            sender=Message.SENDER_AGENT,
            content=masked if self.anonymous else text,
            phase=phase or state.phase,
            element=element if element is not None else state.key,
            kind=kind,
        )
        message.content = text
        return message

    def _record_user(self, response_type: str, content: str) -> Message:
        state = STATES[self.state]
        # 自由記述の回答だけを伏せ字にする (「思いつかない」「特にない」「はい」「いいえ」は選択肢なので残す)
        free_text = response_type == Message.RESPONSE_ANSWER and not state.yes_no
        message = Message.objects.create(
            session=self.session,
            sender=Message.SENDER_USER,
            content=templates.MASK if self.anonymous and free_text else content,
            phase=state.phase,
            element=state.key,
            response_type=response_type,
        )
        message.content = content
        return message

    def _save(self) -> None:
        self.session.state_data = self.data
        if self.state == COMPLETED:
            self.session.current_phase = PHASE_COMPLETED
        self.session.save(update_fields=["state_data", "current_phase", "updated_at"])


def _experience_to_private(experience: Experience) -> dict:
    data = {name: getattr(experience, name) for name in (*PRIVATE_TEXT_FIELDS, *PRIVATE_LIST_FIELDS)}
    if experience.kind == Experience.KIND_RELATED:
        data["relation_type"] = experience.relation_type
        data["evaluation"] = experience.evaluation
    return data
