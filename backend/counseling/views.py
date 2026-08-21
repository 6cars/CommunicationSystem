from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from counseling.models import CounselingSession, Message
from counseling.serializers import MessageSerializer, UserMessageCreateSerializer, UtcDateTimeField
from counseling.strategy.service import DialogueStrategyService


class SessionCreateView(APIView):
    def post(self, request):
        session = CounselingSession.objects.create()
        strategy_service = DialogueStrategyService()
        initial_text = strategy_service.start_session(session)
        Message.objects.create(
            session=session,
            sender=Message.SENDER_AGENT,
            content=initial_text,
            strategy_log={"phase": session.current_phase, "event": "session_start"},
        )
        return Response(
            {
                "session_id": str(session.id),
                "created_at": UtcDateTimeField().to_representation(session.created_at),
                "current_phase": session.current_phase,
                "initial_message": initial_text,
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
        serializer = MessageSerializer(session.messages.all(), many=True)
        return Response(serializer.data)

    def post(self, request, session_id):
        session = self.get_session(session_id)
        if session is None:
            return Response({"detail": "session not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        content = serializer.validated_data["content"]

        user_message = Message.objects.create(
            session=session,
            sender=Message.SENDER_USER,
            content=content,
        )

        result = DialogueStrategyService().handle_user_turn(session, content)
        agent_message = Message.objects.create(
            session=session,
            sender=Message.SENDER_AGENT,
            content=result["reply_text"],
            strategy_log=result.get("strategy_metadata"),
        )

        return Response(
            {
                "user_message": MessageSerializer(user_message).data,
                "agent_message": MessageSerializer(agent_message).data,
                "strategy_info": result.get("strategy_metadata") or {},
            },
            status=status.HTTP_201_CREATED,
        )
