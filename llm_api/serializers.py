"""
serializers.py
リクエスト / レスポンスのバリデーション
"""
from rest_framework import serializers
from django.conf import settings


class MessageSerializer(serializers.Serializer):
    """単一メッセージ (OpenAI互換)"""
    role = serializers.ChoiceField(choices=["system", "user", "assistant"])
    content = serializers.CharField(max_length=32_000)


class ChatRequestSerializer(serializers.Serializer):
    """POST /api/chat/ のリクエストボディ"""
    model = serializers.CharField(
        max_length=100,
        default=None,
        allow_null=True,
        required=False,
        help_text="使用するモデル名。省略時はDEFAULT_MODELを使用。",
    )
    messages = MessageSerializer(many=True, min_length=1)
    temperature = serializers.FloatField(
        min_value=0.0, max_value=2.0, required=False, default=0.7
    )
    top_p = serializers.FloatField(
        min_value=0.0, max_value=1.0, required=False, default=0.9
    )

    def validate_model(self, value):
        if not value:
            return settings.OLLAMA_DEFAULT_MODEL
        return value

    def get_options(self) -> dict:
        data = self.validated_data
        return {
            "temperature": data.get("temperature", 0.7),
            "top_p": data.get("top_p", 0.9),
        }


class ChatResponseSerializer(serializers.Serializer):
    """POST /api/chat/ のレスポンス"""
    model = serializers.CharField()
    content = serializers.CharField()
    done = serializers.BooleanField()
    eval_count = serializers.IntegerField(allow_null=True)
    prompt_eval_count = serializers.IntegerField(allow_null=True)
