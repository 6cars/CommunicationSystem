"""仕様 8章「動作確認」の対話と分岐のテスト。LLM はモックを使う。

実行: DB_ENGINE=sqlite python manage.py test counseling
"""

import csv
import io
import json

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from counseling.dialogue import recall_support
from counseling.models import Experience, Message, RecallSupportLog

FAILURE = {
    "action": "当日ぎりぎりまで資料の準備をしてから家を出た",
    "pre_state": "集合時刻に間に合う時間がある",
    "post_state": "集合時刻に遅刻した",
    "pre_thought": "準備を万全にしてから出発すべきである",
    "post_thought": "準備は前日までに済ませておくべきである",
}


@override_settings(LLM_PROVIDER="mock")
class DialogueFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        res = self.client.post("/api/sessions/", {"user_id": "guest", "name": "テスト"}, format="json")
        self.assertEqual(res.status_code, 201)
        self.session_id = res.data["session_id"]
        self.last = res.data

    # --- helpers -----------------------------------------------------------

    def send(self, response_type="answer", content="", expect=201):
        res = self.client.post(
            f"/api/sessions/{self.session_id}/messages/",
            {"response_type": response_type, "content": content},
            format="json",
        )
        self.assertEqual(res.status_code, expect, res.data)
        self.last = res.data
        return res.data

    def answer(self, content):
        return self.send("answer", content)

    @property
    def agent_texts(self):
        return [m["content"] for m in self.last.get("agent_messages") or self.last.get("initial_messages")]

    @property
    def state(self):
        return self.last["input_state"]["state"]

    def answer_failure_phase(self, post_thought=True):
        self.assertEqual(self.agent_texts[-1], "あなたは，失敗したときどのような行動をとってしまいましたか？")
        self.answer(FAILURE["action"])
        self.assertEqual(
            self.agent_texts,
            ["「当日ぎりぎりまで資料の準備をしてから家を出た」という行動をとる直前，まわりはどのような状態でしたか？"],
        )
        self.answer(FAILURE["pre_state"])
        self.assertEqual(
            self.agent_texts, ["「当日ぎりぎりまで資料の準備をしてから家を出た」という行動の後，どのような状態になりましたか？"]
        )
        self.answer(FAILURE["post_state"])
        self.assertEqual(
            self.agent_texts, ["「当日ぎりぎりまで資料の準備をしてから家を出た」という行動をとる前，どのようなことを考えていましたか？"]
        )
        self.answer(FAILURE["pre_thought"])
        self.assertEqual(self.agent_texts, ["「集合時刻に遅刻した」という結果になったことで，どのようなことを学びましたか？"])
        if post_thought:
            self.answer(FAILURE["post_thought"])
        else:
            self.send("nothing")
        self.assertEqual(self.state, "related1_action")
        self.assertEqual(
            self.agent_texts, ["先ほどお話しいただいた「集合時刻に遅刻した」状態になったとき，どのような行動をとりましたか？"]
        )

    # --- 8. 動作確認: 基本の対話 --------------------------------------------

    def test_main_scenario(self):
        self.answer_failure_phase()

        # 関連経験想起フェーズの最初の質問で「思いつかない」 -> 具体例が提示される
        self.send("dont_know")
        self.assertEqual(self.last["user_message"]["content"], "思いつかない")
        self.assertEqual(self.last["user_message"]["response_type"], "dont_know")
        self.assertEqual(self.last["agent_messages"][0]["kind"], "example")
        self.assertTrue(self.agent_texts[0].startswith("例えば，"))
        self.assertEqual(self.state, "related1_action")

        self.answer("遅れた理由を冗談っぽく話した")
        self.assertEqual(self.agent_texts, ["「遅れた理由を冗談っぽく話した」という行動の後，どのような状態になりましたか？"])
        self.answer("場が和んで打ち解けられた")
        self.assertEqual(self.agent_texts, ["「遅れた理由を冗談っぽく話した」ことで，どのようなことを学びましたか？"])
        self.answer("ユーモアで場の空気を変えられる")
        self.assertEqual(self.agent_texts, ["「遅れた理由を冗談っぽく話した」という経験は，あなたにとって良い経験でしたか？"])
        self.assertEqual(self.last["input_state"]["mode"], "yes_no")

        self.answer("はい")
        self.assertEqual(
            self.agent_texts[0], "「集合時刻に遅刻した」状態が起点となって，「場が和んで打ち解けられた」状態になったのですね．"
        )
        self.assertEqual(self.last["input_state"]["mode"], "closed")

        # 経験DB
        failure = Experience.objects.get(session_id=self.session_id, kind="failure")
        self.assertEqual(failure.action, FAILURE["action"])
        self.assertEqual(failure.pre_states, [FAILURE["pre_state"]])
        self.assertEqual(failure.post_states, [FAILURE["post_state"]])
        self.assertEqual(failure.pre_thought, FAILURE["pre_thought"])
        self.assertEqual(failure.post_thought, FAILURE["post_thought"])
        related = Experience.objects.get(session_id=self.session_id, kind="related")
        self.assertEqual(related.relation_type, 1)
        self.assertEqual(related.pre_states, [FAILURE["post_state"]])
        self.assertEqual(related.action, "遅れた理由を冗談っぽく話した")
        self.assertEqual(related.post_states, ["場が和んで打ち解けられた"])
        self.assertEqual(related.post_thought, "ユーモアで場の空気を変えられる")
        self.assertIs(related.evaluation, True)

        # 経験想起支援のログ
        log = RecallSupportLog.objects.get(session_id=self.session_id)
        self.assertEqual(log.element, "related1_action")
        self.assertEqual(log.attempt, 1)
        self.assertIn("失敗経験の事後状態「集合時刻に遅刻した」を事前状態とし", log.prompt)
        self.assertIn("- 事後思想：準備は前日までに済ませておくべきである", log.prompt)

        # 対話終了後は応答を受け付けない
        self.send("answer", "もう一度", expect=400)

    # --- 8. 分岐 -------------------------------------------------------------

    def test_required_questions_reject_nothing(self):
        # 失敗経験の行動（省略不可）
        self.assertTrue(self.last["input_state"]["required"])
        self.send("nothing", expect=400)
        self.assertEqual(self.state, "failure_action")
        self.answer(FAILURE["action"])
        self.assertFalse(self.last["input_state"]["required"])
        self.send("nothing")  # 事前状態は省略可
        # 失敗経験の事後状態（省略不可）
        self.assertEqual(self.state, "failure_post_state")
        self.assertTrue(self.last["input_state"]["required"])
        self.send("nothing", expect=400)
        self.assertEqual(self.state, "failure_post_state")

    def test_dont_know_repeats_with_different_examples(self):
        self.send("dont_know")
        self.send("dont_know")
        self.send("dont_know")
        logs = list(RecallSupportLog.objects.filter(session_id=self.session_id))
        self.assertEqual([log.attempt for log in logs], [1, 2, 3])
        self.assertEqual(len({log.output for log in logs}), 3)
        self.assertNotIn("これまでに提示した具体例", logs[0].prompt)
        self.assertIn(f"- {logs[0].output}", logs[1].prompt)
        self.assertIn(f"- {logs[1].output}", logs[2].prompt)
        self.assertEqual(self.state, "failure_action")

    def test_type1_nothing_goes_to_type2(self):
        self.answer_failure_phase()
        self.send("nothing")
        self.assertEqual(self.state, "related2_pre_state_action")
        self.assertEqual(
            self.agent_texts,
            ["「準備は前日までに済ませておくべきである」という考えに基づいて行動したことはありますか？そのときの状況と行動を教えてください．"],
        )

    def test_type1_post_state_nothing_goes_to_type2(self):
        self.answer_failure_phase()
        self.answer("謝った")
        self.send("nothing")
        self.assertEqual(self.state, "related2_pre_state_action")

    def test_type2_nothing_goes_to_rerecall_and_new_post_state_is_used(self):
        self.answer_failure_phase()
        self.send("nothing")  # 種類1
        self.send("nothing")  # 種類2
        self.assertEqual(self.state, "rerecall_pre_state")
        self.assertEqual(self.last["input_state"]["phase"], "failure_rerecall")
        self.assertEqual(
            self.agent_texts, ["「当日ぎりぎりまで資料の準備をしてから家を出た」という行動をとる前について，他に思い当たる状況はありますか？"]
        )
        self.send("nothing")
        self.assertEqual(self.state, "rerecall_post_state")
        self.assertTrue(self.last["input_state"]["required"])
        self.assertEqual(
            self.agent_texts, ["「当日ぎりぎりまで資料の準備をしてから家を出た」という行動の後，他にどのような状態になりましたか？"]
        )
        self.send("nothing", expect=400)
        self.answer("友人に迷惑をかけてしまった")
        self.assertEqual(self.state, "related1_action")
        self.assertEqual(
            self.agent_texts,
            ["先ほどお話しいただいた「友人に迷惑をかけてしまった」状態になったとき，どのような行動をとりましたか？"],
        )
        failure = Experience.objects.get(session_id=self.session_id, kind="failure")
        self.assertEqual(failure.post_states, [FAILURE["post_state"], "友人に迷惑をかけてしまった"])

        # 新しい関連経験の事前状態は新たな事後状態になる
        self.answer("お詫びにお菓子を渡した")
        related = Experience.objects.get(session_id=self.session_id, kind="related")
        self.assertEqual(related.pre_states, ["友人に迷惑をかけてしまった"])

    def test_type2_without_failure_post_thought_goes_to_rerecall(self):
        self.answer_failure_phase(post_thought=False)
        self.send("nothing")  # 種類1
        self.assertEqual(self.state, "rerecall_pre_state")

    def test_evaluation_no_asks_another_type1_action(self):
        self.answer_failure_phase()
        self.answer("遅れた理由を冗談っぽく話した")
        self.answer("場が和んだ")
        self.send("nothing")  # 事後思想は省略可 -> 評価へ
        self.assertEqual(self.state, "evaluation")
        self.send("nothing", expect=400)
        self.send("dont_know", expect=400)
        self.send("answer", "たぶん", expect=400)
        self.answer("いいえ")
        self.assertEqual(self.state, "related1_action")
        self.assertEqual(
            self.agent_texts, ["先ほどお話しいただいた「集合時刻に遅刻した」状態になったとき，どのような行動をとりましたか？"]
        )
        self.answer("次の集合に早めに到着した")
        self.answer("信頼を取り戻せた")
        self.answer("早めの行動は安心につながる")
        self.answer("はい")
        related = list(Experience.objects.filter(session_id=self.session_id, kind="related"))
        self.assertEqual([r.evaluation for r in related], [False, True])
        self.assertEqual(
            self.agent_texts[0], "「集合時刻に遅刻した」状態が起点となって，「信頼を取り戻せた」状態になったのですね．"
        )

    def test_type2_positive_presents_thought_origin(self):
        self.answer_failure_phase()
        self.send("nothing")
        self.answer("旅行の前日に荷造りを済ませた")
        self.assertEqual(self.agent_texts, ["「旅行の前日に荷造りを済ませた」という行動の後，どのような状態になりましたか？"])
        self.answer("余裕をもって出発できた")
        self.assertEqual(self.agent_texts, ["「旅行の前日に荷造りを済ませた」という経験は，あなたにとって良い経験でしたか？"])
        self.answer("はい")
        self.assertEqual(
            self.agent_texts[0],
            "「準備は前日までに済ませておくべきである」という学びが起点となって，「余裕をもって出発できた」状態になったのですね．",
        )
        related = Experience.objects.get(session_id=self.session_id, kind="related")
        self.assertEqual(related.relation_type, 2)
        self.assertEqual(related.pre_thought, FAILURE["post_thought"])

    def test_recall_support_error_is_logged_and_state_kept(self):
        with override_settings(LLM_PROVIDER="anthropic"):
            original = recall_support._call_anthropic

            def fail(_prompt):
                raise recall_support.RecallSupportError("boom")

            recall_support._call_anthropic = fail
            try:
                self.send("dont_know")
            finally:
                recall_support._call_anthropic = original
        self.assertEqual(self.last["agent_messages"][0]["kind"], "notice")
        self.assertEqual(self.state, "failure_action")
        log = RecallSupportLog.objects.get(session_id=self.session_id)
        self.assertEqual(log.error, "boom")

    def test_all_templates_render_without_leftover_placeholders(self):
        import re

        from counseling.dialogue import templates
        from counseling.dialogue.controller import DialogueController
        from counseling.dialogue.states import STATES
        from counseling.models import CounselingSession

        variables = DialogueController(CounselingSession.objects.get(id=self.session_id))._variables()
        leftover = re.compile(r"\{[a-z0-9_]+\}")
        for key in STATES:
            if key in ("completed", "evaluation"):
                continue
            prompt = recall_support.build_prompt(key, variables, ["例えば，A"])
            self.assertIsNone(leftover.search(prompt), key)
        for key, value in templates.load_questions().items():
            if key.startswith("_"):
                continue
            for line in value if isinstance(value, list) else [value]:
                self.assertIsNone(leftover.search(templates.fill(line, {**variables, "user_name": "x"})), key)

    # --- 7. ログ -------------------------------------------------------------

    def test_log_export(self):
        self.answer_failure_phase()
        self.send("dont_know")
        self.send("nothing")

        res = self.client.get(f"/api/admin/sessions/{self.session_id}/export/?format=json")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.content)[0]
        user_utterances = [u for u in data["utterances"] if u["speaker"] == "user"]
        self.assertEqual(
            [u["response_type"] for u in user_utterances], ["answer"] * 5 + ["dont_know", "nothing"]
        )
        self.assertEqual(user_utterances[0]["element"], "failure_action")
        self.assertEqual(user_utterances[0]["phase"], "failure_recall")
        self.assertEqual(user_utterances[-1]["phase"], "related_recall")
        self.assertEqual(data["recall_support_calls"][0]["attempt"], 1)
        self.assertEqual(data["failure_experience"]["post_thought"], FAILURE["post_thought"])

        for table in ("utterances", "recall_support", "experiences"):
            res = self.client.get(f"/api/admin/export/?format=csv&table={table}")
            self.assertEqual(res.status_code, 200, table)
            rows = list(csv.reader(io.StringIO(res.content.decode("utf-8-sig"))))
            self.assertGreater(len(rows), 1, table)

        self.assertEqual(self.client.get("/api/admin/export/?format=csv&table=x").status_code, 400)
        self.assertEqual(Message.objects.filter(session_id=self.session_id, sender="agent", kind="example").count(), 1)
