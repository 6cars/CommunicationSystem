"""評価実験用ログの出力（仕様 7章）。JSON とテーブルごとの CSV に対応する。"""

import csv
import io

from counseling.dialogue.states import PHASE_LABELS, STATES
from counseling.models import Account, CounselingSession, Experience, Message

RESPONSE_LABELS = dict(Message.RESPONSE_CHOICES)

CSV_TABLES = ("utterances", "recall_support", "experiences")


def _iso(value) -> str:
    return value.isoformat() if value else ""


def _user_name(session: CounselingSession, names: dict[str, str]) -> str:
    return names.get(session.user_id, session.user_id)


def _account_names(sessions) -> dict[str, str]:
    user_ids = {s.user_id for s in sessions}
    return dict(Account.objects.filter(user_id__in=user_ids).values_list("user_id", "name"))


def _element_label(element: str) -> str:
    state = STATES.get(element)
    return state.label if state else element


def experience_dict(exp: Experience) -> dict:
    return {
        "id": exp.id,
        "kind": exp.kind,
        "relation_type": exp.relation_type,
        "action": exp.action,
        "pre_states": exp.pre_states,
        "post_states": exp.post_states,
        "pre_thought": exp.pre_thought,
        "post_thought": exp.post_thought,
        "pre_state_and_action": exp.pre_state_and_action,
        "evaluation": exp.evaluation,
        "created_at": _iso(exp.created_at),
    }


def session_log(session: CounselingSession, user_name: str | None = None) -> dict:
    """1セッション分のログ（全発話、経験想起支援の呼び出し、経験DB、評価結果）。"""
    if user_name is None:
        user_name = _user_name(session, _account_names([session]))
    experiences = list(session.experiences.all())
    failure = next((e for e in experiences if e.kind == Experience.KIND_FAILURE), None)
    related = [e for e in experiences if e.kind == Experience.KIND_RELATED]
    positive = next((e for e in related if e.evaluation is True), None)

    return {
        "session_id": str(session.id),
        "user_id": session.user_id,
        "user_name": user_name,
        "created_at": _iso(session.created_at),
        "updated_at": _iso(session.updated_at),
        "current_phase": session.current_phase,
        "completed": session.current_phase == "completed",
        "utterances": [
            {
                "seq": i + 1,
                "speaker": m.sender,
                "text": m.content,
                "timestamp": _iso(m.created_at),
                "phase": m.phase,
                "phase_label": PHASE_LABELS.get(m.phase, m.phase),
                "element": m.element,
                "element_label": _element_label(m.element),
                "response_type": m.response_type,
                "response_type_label": RESPONSE_LABELS.get(m.response_type, ""),
                "kind": m.kind,
                "message_id": str(m.id),
            }
            for i, m in enumerate(session.messages.all())
        ],
        "recall_support_calls": [
            {
                "timestamp": _iso(log.created_at),
                "phase": log.phase,
                "element": log.element,
                "element_label": _element_label(log.element),
                "attempt": log.attempt,
                "prompt": log.prompt,
                "raw_output": log.raw_output,
                "output": log.output,
                "model": log.model,
                "error": log.error,
                "message_id": str(log.message_id) if log.message_id else None,
            }
            for log in session.recall_support_logs.all()
        ],
        "failure_experience": experience_dict(failure) if failure else None,
        "related_experiences": [experience_dict(e) for e in related],
        "evaluation_results": [{"related_experience_id": e.id, "evaluation": e.evaluation} for e in related],
        "positive_related_experience_id": positive.id if positive else None,
    }


def sessions_log(sessions) -> list[dict]:
    sessions = list(sessions)
    names = _account_names(sessions)
    return [session_log(s, _user_name(s, names)) for s in sessions]


def sessions_csv(sessions, table: str) -> str:
    """table: utterances / recall_support / experiences"""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    logs = sessions_log(sessions)

    if table == "utterances":
        writer.writerow([
            "session_id", "user_id", "user_name", "seq", "timestamp", "speaker", "text",
            "phase", "phase_label", "element", "element_label", "response_type", "response_type_label", "kind",
        ])
        for log in logs:
            for u in log["utterances"]:
                writer.writerow([
                    log["session_id"], log["user_id"], log["user_name"], u["seq"], u["timestamp"], u["speaker"],
                    u["text"], u["phase"], u["phase_label"], u["element"], u["element_label"],
                    u["response_type"], u["response_type_label"], u["kind"],
                ])
    elif table == "recall_support":
        writer.writerow([
            "session_id", "user_id", "user_name", "timestamp", "phase", "element", "element_label",
            "attempt", "model", "prompt", "raw_output", "output", "error",
        ])
        for log in logs:
            for c in log["recall_support_calls"]:
                writer.writerow([
                    log["session_id"], log["user_id"], log["user_name"], c["timestamp"], c["phase"], c["element"],
                    c["element_label"], c["attempt"], c["model"], c["prompt"], c["raw_output"], c["output"], c["error"],
                ])
    elif table == "experiences":
        writer.writerow([
            "session_id", "user_id", "user_name", "experience_id", "kind", "relation_type", "action",
            "pre_states", "post_states", "pre_thought", "post_thought", "pre_state_and_action", "evaluation",
        ])
        for log in logs:
            exps = ([log["failure_experience"]] if log["failure_experience"] else []) + log["related_experiences"]
            for e in exps:
                writer.writerow([
                    log["session_id"], log["user_id"], log["user_name"], e["id"], e["kind"], e["relation_type"] or "",
                    e["action"], " / ".join(e["pre_states"]), " / ".join(e["post_states"]), e["pre_thought"],
                    e["post_thought"], e["pre_state_and_action"],
                    "" if e["evaluation"] is None else ("yes" if e["evaluation"] else "no"),
                ])
    else:
        raise ValueError(f"unknown table: {table}")
    # Excel で文字化けしないよう BOM を付ける
    return "﻿" + buffer.getvalue()
