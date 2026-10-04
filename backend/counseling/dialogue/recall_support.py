"""経験想起支援機能（仕様 5章）。

ユーザが「思いつかない」を押したとき、尋ねている要素のプロンプトテンプレートに
これまでの回答を埋め込み、LLM で回答の具体例を1つ生成する。
LLM を使うのはこの機能だけで、質問文の生成には使わない。
"""

import os
from dataclasses import dataclass

from django.conf import settings

from counseling.dialogue import templates

FALLBACK_BETA = "server-side-fallback-2026-07-01"


class RecallSupportError(Exception):
    pass


@dataclass
class RecallSupportResult:
    prompt: str
    raw_output: str = ""
    output: str = ""
    model: str = ""
    error: str = ""


def build_prompt(element: str, variables: dict[str, str], previous_examples: list[str]) -> str:
    """要素ごとのテンプレートに変数を埋め込む。2回目以降はそれまでの具体例を含める。"""
    section = ""
    if previous_examples:
        listed = "\n".join(f"- {example}" for example in previous_examples)
        section = templates.fill(templates.load_previous_examples_section(), {"previous_examples": listed})
    return templates.fill(
        templates.load_recall_support_template(element),
        {**variables, "previous_examples_section": section},
    )


def normalize_output(raw: str) -> str:
    """LLM 出力から1文の問いかけを取り出す（前後の空白やコードフェンスを除き、最初の行を使う）。"""
    for line in raw.strip().splitlines():
        line = line.strip().strip("`").strip()
        if line:
            return line
    return ""


def generate_example(element: str, variables: dict[str, str], previous_examples: list[str]) -> RecallSupportResult:
    result = RecallSupportResult(prompt=build_prompt(element, variables, previous_examples))
    try:
        if settings.LLM_PROVIDER == "mock":
            result.raw_output, result.model = _call_mock(element, len(previous_examples) + 1)
        elif settings.LLM_PROVIDER == "anthropic":
            result.raw_output, result.model = _call_anthropic(result.prompt)
        else:
            result.raw_output, result.model = _call_openai(result.prompt)
        result.output = normalize_output(result.raw_output)
        if not result.output:
            raise RecallSupportError("LLM の出力が空でした")
    except RecallSupportError as exc:
        result.error = str(exc)
    return result


def _call_mock(element: str, attempt: int) -> tuple[str, str]:
    return f"例えば，「（{element} の具体例 {attempt}）」という経験はありませんか？", "mock"


def _call_openai(prompt: str) -> tuple[str, str]:
    import openai

    # docker compose はキー未設定でも空文字を渡すため、空の場合もここで止める
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        raise RecallSupportError(
            "OPENAI_API_KEY が設定されていません（リポジトリ直下の .env に書いてコンテナを作り直してください）"
        )
    try:
        client = openai.OpenAI(timeout=settings.LLM_TIMEOUT_SECONDS)
        response = client.responses.create(
            model=settings.LLM_MODEL,
            input=prompt,
            max_output_tokens=settings.LLM_MAX_TOKENS,
        )
    except openai.APIStatusError as exc:
        raise RecallSupportError(f"OpenAI API エラー (HTTP {exc.status_code}): {exc.message}") from exc
    except openai.APIConnectionError as exc:
        raise RecallSupportError(f"OpenAI API に接続できませんでした: {exc}") from exc
    except openai.OpenAIError as exc:
        raise RecallSupportError(f"OpenAI API を呼び出せませんでした: {exc}") from exc

    if response.status == "incomplete":
        reason = response.incomplete_details.reason if response.incomplete_details else "unknown"
        raise RecallSupportError(f"OpenAI API の応答が途中で終了しました (reason={reason})")
    return response.output_text, response.model


def _call_anthropic(prompt: str) -> tuple[str, str]:
    import anthropic

    params = {
        "model": settings.LLM_MODEL,
        "max_tokens": settings.LLM_MAX_TOKENS,
        "messages": [{"role": "user", "content": prompt}],
    }
    if settings.LLM_EFFORT:
        params["output_config"] = {"effort": settings.LLM_EFFORT}

    try:
        client = anthropic.Anthropic(timeout=settings.LLM_TIMEOUT_SECONDS)
        if settings.LLM_USE_FALLBACKS:
            response = client.beta.messages.create(betas=[FALLBACK_BETA], fallbacks="default", **params)
        else:
            response = client.messages.create(**params)
    except anthropic.APIStatusError as exc:
        raise RecallSupportError(f"Claude API エラー (HTTP {exc.status_code}): {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise RecallSupportError(f"Claude API に接続できませんでした: {exc}") from exc
    except (anthropic.AnthropicError, TypeError) as exc:
        # TypeError: ANTHROPIC_API_KEY などの認証情報が設定されていない場合に SDK が送出する
        raise RecallSupportError(f"Claude API を呼び出せませんでした: {exc}") from exc

    if response.stop_reason == "refusal":
        raise RecallSupportError("Claude API が応答を拒否しました (stop_reason=refusal)")
    text = "".join(block.text for block in response.content if block.type == "text")
    return text, response.model
