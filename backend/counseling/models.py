import uuid

from django.db import models


class Account(models.Model):
    user_id = models.CharField(max_length=64, primary_key=True, help_text="ユーザーID (一意)")
    name = models.CharField(max_length=128, help_text="名前 / 表示名")
    password = models.CharField(max_length=256, help_text="パスワード")
    is_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.user_id})"


class CounselingSession(models.Model):
    PHASE_INITIAL = "initial"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.CharField(max_length=128, default="guest", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    current_phase = models.CharField(max_length=64, default=PHASE_INITIAL)
    state_data = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.user_id}] {self.id} ({self.current_phase})"


class Message(models.Model):
    SENDER_USER = "user"
    SENDER_AGENT = "agent"
    SENDER_CHOICES = [
        (SENDER_USER, "user"),
        (SENDER_AGENT, "agent"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        CounselingSession,
        related_name="messages",
        on_delete=models.CASCADE,
    )
    RESPONSE_ANSWER = "answer"
    RESPONSE_DONT_KNOW = "dont_know"
    RESPONSE_NOTHING = "nothing"
    RESPONSE_CHOICES = [
        (RESPONSE_ANSWER, "回答"),
        (RESPONSE_DONT_KNOW, "思いつかない"),
        (RESPONSE_NOTHING, "特にない"),
    ]

    sender = models.CharField(max_length=16, choices=SENDER_CHOICES)
    content = models.TextField()
    # 発話時点のフェーズと、尋ねていた（ユーザ発話なら回答対象の）要素
    phase = models.CharField(max_length=32, blank=True, default="")
    element = models.CharField(max_length=64, blank=True, default="")
    # ユーザ発話の応答種別（エージェント発話では空）
    response_type = models.CharField(max_length=16, blank=True, default="", choices=RESPONSE_CHOICES)
    # エージェント発話の種類（greeting / question / example / origin / closing / notice）
    kind = models.CharField(max_length=16, blank=True, default="")
    strategy_log = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender}: {self.content[:40]}"


class Experience(models.Model):
    """経験DB: 失敗経験・関連経験の各要素を保存する。"""

    KIND_FAILURE = "failure"
    KIND_RELATED = "related"
    KIND_CHOICES = [
        (KIND_FAILURE, "失敗経験"),
        (KIND_RELATED, "関連経験"),
    ]

    session = models.ForeignKey(
        CounselingSession,
        related_name="experiences",
        on_delete=models.CASCADE,
    )
    kind = models.CharField(max_length=16, choices=KIND_CHOICES)
    # 関連経験の種類 (1: 失敗経験の事後状態を事前状態とする / 2: 失敗経験の事後思想を事前思想とする)
    relation_type = models.PositiveSmallIntegerField(null=True, blank=True)
    action = models.TextField(blank=True, default="")
    pre_states = models.JSONField(default=list, blank=True)
    post_states = models.JSONField(default=list, blank=True)
    pre_thought = models.TextField(blank=True, default="")
    post_thought = models.TextField(blank=True, default="")
    # 種類2では「事前状態と行動」を1つの質問で尋ねるため、回答をそのまま保存する
    pre_state_and_action = models.TextField(blank=True, default="")
    # 評価の結果 (None: 未評価)
    evaluation = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.kind}{self.relation_type or ''}: {self.action or self.pre_state_and_action}"[:60]


class RecallSupportLog(models.Model):
    """経験想起支援機能の呼び出しログ。"""

    session = models.ForeignKey(
        CounselingSession,
        related_name="recall_support_logs",
        on_delete=models.CASCADE,
    )
    message = models.ForeignKey(
        Message,
        related_name="recall_support_logs",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    phase = models.CharField(max_length=32)
    element = models.CharField(max_length=64)
    # 同じ質問に対して何回目の具体例か (1始まり)
    attempt = models.PositiveIntegerField()
    prompt = models.TextField()
    raw_output = models.TextField(blank=True, default="")
    output = models.TextField(blank=True, default="")
    model = models.CharField(max_length=64, blank=True, default="")
    error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
