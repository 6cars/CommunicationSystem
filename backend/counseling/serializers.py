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
        fields = ["id", "sender", "content", "created_at"]


class UserMessageCreateSerializer(serializers.Serializer):
    content = serializers.CharField(allow_blank=False, trim_whitespace=True)
