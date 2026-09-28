"""対話戦略（仕様 3章）の状態と遷移の定義。

各状態は「1つの要素を尋ねている状態」に対応する。ユーザの応答によって
「回答を得た (answered)」か「回答を得なかった (skipped)」かが決まり、
TRANSITIONS に従って次の状態へ遷移する。

状態遷移の一覧は docs/state_machine.md にもまとめている。
"""

from dataclasses import dataclass

# フェーズ
PHASE_FAILURE_RECALL = "failure_recall"  # 失敗経験想起フェーズ
PHASE_RELATED_RECALL = "related_recall"  # 関連経験想起フェーズ
PHASE_FAILURE_RERECALL = "failure_rerecall"  # 失敗経験再想起フェーズ
PHASE_COMPLETED = "completed"

PHASE_LABELS = {
    PHASE_FAILURE_RECALL: "失敗経験想起フェーズ",
    PHASE_RELATED_RECALL: "関連経験想起フェーズ",
    PHASE_FAILURE_RERECALL: "失敗経験再想起フェーズ",
    PHASE_COMPLETED: "終了",
}

# 状態（= 尋ねる要素）
FAILURE_ACTION = "failure_action"
FAILURE_PRE_STATE = "failure_pre_state"
FAILURE_POST_STATE = "failure_post_state"
FAILURE_PRE_THOUGHT = "failure_pre_thought"
FAILURE_POST_THOUGHT = "failure_post_thought"
RELATED1_ACTION = "related1_action"
RELATED1_POST_STATE = "related1_post_state"
RELATED1_POST_THOUGHT = "related1_post_thought"
RELATED2_PRE_STATE_ACTION = "related2_pre_state_action"
RELATED2_POST_STATE = "related2_post_state"
EVALUATION = "evaluation"
RERECALL_PRE_STATE = "rerecall_pre_state"
RERECALL_POST_STATE = "rerecall_post_state"
COMPLETED = "completed"

# 遷移先として使う擬似状態: [種類2の想起] の入口
# 失敗経験の事後思想が得られていなければ失敗経験再想起フェーズへ、得られていれば種類2の質問へ進む
TYPE2_ENTRY = "type2_entry"


@dataclass(frozen=True)
class State:
    key: str
    phase: str
    label: str
    # 省略不可なら「特にない」を受け付けない
    required: bool = False
    # 「はい／いいえ」で答える質問
    yes_no: bool = False


STATES: dict[str, State] = {
    s.key: s
    for s in [
        State(FAILURE_ACTION, PHASE_FAILURE_RECALL, "失敗経験の行動", required=True),
        State(FAILURE_PRE_STATE, PHASE_FAILURE_RECALL, "失敗経験の事前状態"),
        State(FAILURE_POST_STATE, PHASE_FAILURE_RECALL, "失敗経験の事後状態", required=True),
        State(FAILURE_PRE_THOUGHT, PHASE_FAILURE_RECALL, "失敗経験の事前思想"),
        State(FAILURE_POST_THOUGHT, PHASE_FAILURE_RECALL, "失敗経験の事後思想"),
        State(RELATED1_ACTION, PHASE_RELATED_RECALL, "関連経験(種類1)の行動"),
        State(RELATED1_POST_STATE, PHASE_RELATED_RECALL, "関連経験(種類1)の事後状態"),
        State(RELATED1_POST_THOUGHT, PHASE_RELATED_RECALL, "関連経験(種類1)の事後思想"),
        State(RELATED2_PRE_STATE_ACTION, PHASE_RELATED_RECALL, "関連経験(種類2)の事前状態と行動"),
        State(RELATED2_POST_STATE, PHASE_RELATED_RECALL, "関連経験(種類2)の事後状態"),
        State(EVALUATION, PHASE_RELATED_RECALL, "関連経験の評価", required=True, yes_no=True),
        State(RERECALL_PRE_STATE, PHASE_FAILURE_RERECALL, "失敗経験の別の事前状態"),
        State(RERECALL_POST_STATE, PHASE_FAILURE_RERECALL, "失敗経験の別の事後状態", required=True),
        State(COMPLETED, PHASE_COMPLETED, "終了"),
    ]
}

# 状態 -> {"answered": 回答を得たときの遷移先, "skipped": 回答を得なかったときの遷移先}
# 評価は {"yes": ..., "no": ...}
TRANSITIONS: dict[str, dict[str, str]] = {
    # 3.2 失敗経験想起フェーズ
    FAILURE_ACTION: {"answered": FAILURE_PRE_STATE},
    FAILURE_PRE_STATE: {"answered": FAILURE_POST_STATE, "skipped": FAILURE_POST_STATE},
    FAILURE_POST_STATE: {"answered": FAILURE_PRE_THOUGHT},
    FAILURE_PRE_THOUGHT: {"answered": FAILURE_POST_THOUGHT, "skipped": FAILURE_POST_THOUGHT},
    FAILURE_POST_THOUGHT: {"answered": RELATED1_ACTION, "skipped": RELATED1_ACTION},
    # 3.3 関連経験想起フェーズ [種類1の想起]
    RELATED1_ACTION: {"answered": RELATED1_POST_STATE, "skipped": TYPE2_ENTRY},
    RELATED1_POST_STATE: {"answered": RELATED1_POST_THOUGHT, "skipped": TYPE2_ENTRY},
    RELATED1_POST_THOUGHT: {"answered": EVALUATION, "skipped": EVALUATION},
    # 3.3 関連経験想起フェーズ [種類2の想起]
    RELATED2_PRE_STATE_ACTION: {"answered": RELATED2_POST_STATE, "skipped": RERECALL_PRE_STATE},
    RELATED2_POST_STATE: {"answered": EVALUATION, "skipped": RERECALL_PRE_STATE},
    # 3.3 関連経験想起フェーズ [評価]
    EVALUATION: {"yes": COMPLETED, "no": RELATED1_ACTION},
    # 3.4 失敗経験再想起フェーズ
    RERECALL_PRE_STATE: {"answered": RERECALL_POST_STATE, "skipped": RERECALL_POST_STATE},
    RERECALL_POST_STATE: {"answered": RELATED1_ACTION},
}

INITIAL_STATE = FAILURE_ACTION
