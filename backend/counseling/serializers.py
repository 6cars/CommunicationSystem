from rest_framework import serializers

from counseling.models import Message


class UtcDateTimeField(serializers.DateTimeField):
    def to_representation(self, value):
        if value is None:
            return None
        from django.utils.timezone import localtime
        from datetime import timezone

        aware = localtime(value, timezone.utc)
        return aware.strftime("%Y-%m-%dT%H:%M:%SZ")


class MessageSerializer(serializers.ModelSerializer):
    created_at = UtcDateTimeField(read_only=True)

    class Meta:
        model = Message
        fields = ["id", "sender", "content", "phase", "element", "response_type", "kind", "created_at"]


class UserResponseSerializer(serializers.Serializer):
    response_type = serializers.ChoiceField(
        choices=[Message.RESPONSE_ANSWER, Message.RESPONSE_DONT_KNOW, Message.RESPONSE_NOTHING],
        default=Message.RESPONSE_ANSWER,
    )
    content = serializers.CharField(allow_blank=True, trim_whitespace=True, required=False, default="")
