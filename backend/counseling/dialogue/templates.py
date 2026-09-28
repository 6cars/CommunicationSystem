"""外部ファイル (PROMPTS_DIR) に置いたテンプレートの読み込みと変数埋め込み。

ファイルは呼び出しのたびに読み込むので、サーバを再起動せずにテンプレートを編集できる。
"""

import json
import re

from django.conf import settings

UNANSWERED = "未回答"

_PLACEHOLDER = re.compile(r"\{([a-z0-9_]+)\}")


def fill(template: str, variables: dict[str, str]) -> str:
    """{name} を variables[name] で置き換える。値が空なら「未回答」、未知の変数はそのまま残す。"""

    def replace(match: re.Match) -> str:
        name = match.group(1)
        if name not in variables:
            return match.group(0)
        return variables[name] or UNANSWERED

    return _PLACEHOLDER.sub(replace, template)


def load_questions() -> dict:
    path = settings.PROMPTS_DIR / "questions.json"
    return json.loads(path.read_text(encoding="utf-8"))


def question_text(key: str, variables: dict[str, str]) -> str:
    return fill(load_questions()[key], variables)


def question_lines(key: str, variables: dict[str, str]) -> list[str]:
    value = load_questions()[key]
    lines = value if isinstance(value, list) else [value]
    return [fill(line, variables) for line in lines]


def load_recall_support_template(element: str) -> str:
    path = settings.PROMPTS_DIR / "recall_support" / f"{element}.txt"
    return path.read_text(encoding="utf-8")


def load_previous_examples_section() -> str:
    path = settings.PROMPTS_DIR / "recall_support" / "_previous_examples.txt"
    return path.read_text(encoding="utf-8")
