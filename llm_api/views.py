"""
views.py
REST APIエンドポイント

エンドポイント一覧:
  POST /api/chat/          - 通常チャット (同期)
  POST /api/chat/stream/   - ストリーミングチャット (Server-Sent Events)
  GET  /api/models/        - インストール済みモデル一覧
  GET  /api/health/        - ヘルスチェック
"""
import json
from django.http import StreamingHttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import ChatRequestSerializer
from .ollama_client import ollama, OllamaConnectionError, OllamaModelError, OllamaError


# ── チャット（同期）────────────────────────────────────────────────
class ChatView(APIView):
    """
    POST /api/chat/

    リクエスト例:
      {
        "model": "llama3.2",          // 省略可 (settings.OLLAMA_DEFAULT_MODEL を使用)
        "messages": [
          {"role": "system",    "content": "あなたは親切なアシスタントです。"},
          {"role": "user",      "content": "Pythonとは何ですか？"}
        ],
        "temperature": 0.7,           // 省略可
        "top_p": 0.9                  // 省略可
      }

    レスポンス例:
      {
        "model": "llama3.2",
        "content": "Pythonは...",
        "done": true,
        "eval_count": 120,
        "prompt_eval_count": 30
      }
    """

    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "リクエストが不正です", "detail": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        try:
            result = ollama.chat(
                model=data["model"],
                messages=data["messages"],
                options=serializer.get_options(),
            )
        except OllamaConnectionError as e:
            return Response(
                {"error": "Ollamaサーバーに接続できません", "detail": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except OllamaModelError as e:
            return Response(
                {"error": "モデルが見つかりません", "detail": str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except OllamaError as e:
            return Response(
                {"error": "Ollamaエラー", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(result, status=status.HTTP_200_OK)


# ── チャット（ストリーミング）──────────────────────────────────────
class ChatStreamView(APIView):
    """
    POST /api/chat/stream/

    Server-Sent Events (SSE) 形式でトークンをストリーミング返却。
    各チャンクは data: {"token": "..."}\n\n 形式。
    完了時は data: {"done": true}\n\n を送信。

    リクエスト形式は /api/chat/ と同じ。
    """

    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "リクエストが不正です", "detail": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        def event_stream():
            try:
                for token in ollama.chat_stream(
                    model=data["model"],
                    messages=data["messages"],
                    options=serializer.get_options(),
                ):
                    payload = json.dumps({"token": token}, ensure_ascii=False)
                    yield f"data: {payload}\n\n"
                yield 'data: {"done": true}\n\n'
            except OllamaConnectionError as e:
                err = json.dumps({"error": str(e)}, ensure_ascii=False)
                yield f"data: {err}\n\n"
            except OllamaError as e:
                err = json.dumps({"error": str(e)}, ensure_ascii=False)
                yield f"data: {err}\n\n"

        response = StreamingHttpResponse(
            event_stream(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


# ── モデル一覧 ─────────────────────────────────────────────────────
class ModelListView(APIView):
    """
    GET /api/models/

    レスポンス例:
      {
        "models": [
          {"name": "llama3.2:latest", "size_gb": 2.02, "modified_at": "2024-..."},
          ...
        ]
      }
    """

    def get(self, request):
        try:
            models = ollama.list_models()
        except OllamaConnectionError as e:
            return Response(
                {"error": "Ollamaサーバーに接続できません", "detail": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except OllamaError as e:
            return Response(
                {"error": "Ollamaエラー", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response({"models": models})


# ── ヘルスチェック ─────────────────────────────────────────────────
class HealthView(APIView):
    """
    GET /api/health/

    OllamaサーバーへのPingとDjangoの稼働確認。
    """

    def get(self, request):
        try:
            models = ollama.list_models()
            ollama_status = "ok"
            model_count = len(models)
        except OllamaConnectionError:
            ollama_status = "unreachable"
            model_count = 0
        except OllamaError:
            ollama_status = "error"
            model_count = 0

        return Response(
            {
                "django": "ok",
                "ollama": ollama_status,
                "model_count": model_count,
            },
            status=status.HTTP_200_OK if ollama_status == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE,
        )
