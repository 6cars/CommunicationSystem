import re

import json

from django.contrib.auth.hashers import check_password, make_password
from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from counseling import export
from counseling.dialogue.controller import DialogueController, DialogueError
from counseling.models import Account, CounselingSession, Message
from counseling.serializers import MessageSerializer, UserResponseSerializer, UtcDateTimeField


def generate_next_user_id() -> str:
    """自動で重複のない連番ユーザーID (user_001, user_002, ...) を発行"""
    existing_ids = list(Account.objects.exclude(user_id="admin").values_list("user_id", flat=True))
    max_num = 0
    for uid in existing_ids:
        match = re.match(r"^user_(\d+)$", uid)
        if match:
            try:
                max_num = max(max_num, int(match.group(1)))
            except ValueError:
                pass

    next_num = max_num + 1
    candidate = f"user_{next_num:03d}"
    while candidate in existing_ids or Account.objects.filter(user_id=candidate).exists():
        next_num += 1
        candidate = f"user_{next_num:03d}"
    return candidate


class AuthRegisterView(APIView):
    """新規アカウント登録（お名前とパスワードのみ。ユーザーIDは内部管理）"""
    def post(self, request):
        name = (request.data.get("name") or "").strip()
        password = (request.data.get("password") or "").strip()

        if not name:
            return Response({"detail": "お名前を入力してください"}, status=status.HTTP_400_BAD_REQUEST)
        if name.lower() == "admin":
            return Response({"detail": "「admin」はお名前に使用できません"}, status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({"detail": "パスワードを入力してください"}, status=status.HTTP_400_BAD_REQUEST)

        if Account.objects.filter(name=name).exists():
            return Response({"detail": "このお名前は既に登録されています。他のお名前をご使用ください。"}, status=status.HTTP_400_BAD_REQUEST)

        user_id = generate_next_user_id()
        account = Account.objects.create(
            user_id=user_id,
            name=name,
            password=make_password(password),
            is_admin=False,
        )

        return Response(
            {
                "user_id": account.user_id,
                "name": account.name,
                "role": "user",
            },
            status=status.HTTP_201_CREATED,
        )


class AuthLoginView(APIView):
    """統一ログイン認証（お名前とパスワード）"""
    def post(self, request):
        identifier = (request.data.get("name") or request.data.get("user_id") or request.data.get("username") or "").strip()
        password = (request.data.get("password") or "").strip()

        if not identifier:
            return Response({"detail": "お名前を入力してください"}, status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({"detail": "パスワードを入力してください"}, status=status.HTTP_400_BAD_REQUEST)

        # 管理者ログインチェック (admin / admin)
        if identifier.lower() == "admin":
            if password == "admin":
                admin_account, _ = Account.objects.get_or_create(
                    user_id="admin",
                    defaults={"name": "管理者", "password": make_password("admin"), "is_admin": True},
                )
                return Response({
                    "role": "admin",
                    "user_id": "admin",
                    "name": admin_account.name,
                })
            return Response(
                {"detail": "パスワードが正しくありません"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 一般ユーザー認証（お名前またはIDで照合）
        account = Account.objects.filter(name=identifier).first() or Account.objects.filter(user_id=identifier).first()
        if not account or not check_password(password, account.password):
            return Response(
                {"detail": "お名前またはパスワードが正しくありません"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            "role": "admin" if account.is_admin else "user",
            "user_id": account.user_id,
            "name": account.name,
        })


class SessionCreateView(APIView):
    def post(self, request):
        user_id = (request.data.get("user_id") or "guest").strip() or "guest"
        user_name = (request.data.get("name") or "").strip()

        # ユーザー名がリクエストにない場合は Account テーブルから取得
        if not user_name and user_id != "guest":
            account = Account.objects.filter(user_id=user_id).first()
            if account and account.name:
                user_name = account.name
        if not user_name:
            user_name = user_id if user_id != "guest" else "ゲスト"

        session = CounselingSession.objects.create(user_id=user_id)
        initial_messages = DialogueController.start(session, user_name=user_name)
        controller = DialogueController(session)

        return Response(
            {
                "session_id": str(session.id),
                "user_id": session.user_id,
                "created_at": UtcDateTimeField().to_representation(session.created_at),
                "current_phase": session.current_phase,
                "initial_messages": MessageSerializer(initial_messages, many=True).data,
                "input_state": controller.input_state(),
            },
            status=status.HTTP_201_CREATED,
        )


class SessionMessageView(APIView):
    def get_session(self, session_id):
        return CounselingSession.objects.filter(id=session_id).first()

    def get(self, request, session_id):
        session = self.get_session(session_id)
        if session is None:
            return Response({"detail": "session not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            {
                "messages": MessageSerializer(session.messages.all(), many=True).data,
                "input_state": DialogueController(session).input_state(),
            }
        )

    def post(self, request, session_id):
        """ユーザの応答 (response_type: answer / dont_know / nothing) を受け取り、次の発話を返す。"""
        session = self.get_session(session_id)
        if session is None:
            return Response({"detail": "session not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        controller = DialogueController(session)
        try:
            user_message, agent_messages = controller.handle(
                serializer.validated_data["response_type"],
                serializer.validated_data["content"],
            )
        except DialogueError as exc:
            return Response(
                {"detail": str(exc), "input_state": controller.input_state()},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "user_message": MessageSerializer(user_message).data,
                "agent_messages": MessageSerializer(agent_messages, many=True).data,
                "input_state": controller.input_state(),
            },
            status=status.HTTP_201_CREATED,
        )


class AdminUserListView(APIView):
    """管理者用: 登録アカウント一覧（adminアカウントは除外）"""
    def get(self, request):
        accounts = Account.objects.exclude(user_id="admin").exclude(is_admin=True).order_by("-created_at")
        data = []
        for acc in accounts:
            session_qs = CounselingSession.objects.filter(user_id=acc.user_id)
            session_count = session_qs.count()
            message_count = Message.objects.filter(session__user_id=acc.user_id).count()
            last_sess = session_qs.order_by("-updated_at").first()
            last_activity = last_sess.updated_at if last_sess else acc.created_at

            data.append({
                "user_id": acc.user_id,
                "name": acc.name,
                "is_admin": acc.is_admin,
                "session_count": session_count,
                "message_count": message_count,
                "last_activity": UtcDateTimeField().to_representation(last_activity),
                "created_at": UtcDateTimeField().to_representation(acc.created_at),
            })
        return Response(data)


class AdminUserDeleteView(APIView):
    """管理者用: ユーザーアカウントおよび対話ログの削除"""
    def delete(self, request, user_id):
        if user_id.lower() == "admin":
            return Response({"detail": "管理者アカウントは削除できません"}, status=status.HTTP_400_BAD_REQUEST)

        # セッションおよびメッセージの削除
        CounselingSession.objects.filter(user_id=user_id).delete()
        # アカウントの削除
        Account.objects.filter(user_id=user_id).delete()

        return Response({"success": True, "detail": "ユーザーを削除しました"})


class AdminUserSessionsView(APIView):
    """管理者用: 特定ユーザーのセッション一覧"""
    def get(self, request, user_id):
        account = Account.objects.filter(user_id=user_id).first()
        user_name = account.name if account else user_id
        sessions = CounselingSession.objects.filter(user_id=user_id).order_by("-created_at")
        data = []
        for s in sessions:
            first_user_msg = s.messages.filter(sender=Message.SENDER_USER).first()
            data.append({
                "session_id": str(s.id),
                "user_id": s.user_id,
                "user_name": user_name,
                "created_at": UtcDateTimeField().to_representation(s.created_at),
                "updated_at": UtcDateTimeField().to_representation(s.updated_at),
                "current_phase": s.current_phase,
                "message_count": s.messages.count(),
                "preview_text": first_user_msg.content if first_user_msg else "(メッセージなし)",
            })
        return Response(data)


class AdminSessionDetailView(APIView):
    """管理者用: 特定セッションの対話ログ詳細（全発話・経験DB・経験想起支援の呼び出し）"""
    def get(self, request, session_id):
        session = CounselingSession.objects.filter(id=session_id).first()
        if not session:
            return Response({"detail": "session not found"}, status=status.HTTP_404_NOT_FOUND)
        log = export.session_log(session)
        return Response({
            **log,
            "created_at": UtcDateTimeField().to_representation(session.created_at),
            "updated_at": UtcDateTimeField().to_representation(session.updated_at),
            "messages": [
                {
                    "id": u["message_id"],
                    "sender": u["speaker"],
                    "content": u["text"],
                    "phase": u["phase"],
                    "phase_label": u["phase_label"],
                    "element": u["element"],
                    "element_label": u["element_label"],
                    "response_type": u["response_type"],
                    "response_type_label": u["response_type_label"],
                    "kind": u["kind"],
                    "created_at": u["timestamp"],
                }
                for u in log["utterances"]
            ],
        })


def _export_response(sessions, fmt: str, table: str, basename: str):
    if fmt == "csv":
        if table not in export.CSV_TABLES:
            return Response(
                {"detail": f"table は {', '.join(export.CSV_TABLES)} のいずれかを指定してください"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        response = HttpResponse(export.sessions_csv(sessions, table), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{basename}_{table}.csv"'
        return response
    if fmt == "json":
        body = json.dumps(export.sessions_log(sessions), ensure_ascii=False, indent=2)
        response = HttpResponse(body, content_type="application/json; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{basename}.json"'
        return response
    return Response({"detail": "format は json か csv を指定してください"}, status=status.HTTP_400_BAD_REQUEST)


class AdminSessionExportView(APIView):
    """管理者用: 1セッションのログ出力 (?format=json|csv&table=utterances|recall_support|experiences)"""
    def get(self, request, session_id):
        sessions = CounselingSession.objects.filter(id=session_id)
        if not sessions.exists():
            return Response({"detail": "session not found"}, status=status.HTTP_404_NOT_FOUND)
        return _export_response(
            sessions,
            request.query_params.get("format", "json"),
            request.query_params.get("table", "utterances"),
            f"session_{str(session_id)[:8]}",
        )


class AdminExportView(APIView):
    """管理者用: 全セッション（?user_id= で絞り込み可）のログ出力"""
    def get(self, request):
        sessions = CounselingSession.objects.order_by("created_at")
        user_id = request.query_params.get("user_id")
        if user_id:
            sessions = sessions.filter(user_id=user_id)
        return _export_response(
            sessions,
            request.query_params.get("format", "json"),
            request.query_params.get("table", "utterances"),
            f"sessions_{user_id}" if user_id else "sessions_all",
        )
