"""
ollama_client.py
Ollama REST API との通信ラッパー
"""
import json
import requests
from django.conf import settings


class OllamaError(Exception):
    """Ollama通信エラー基底クラス"""
    pass


class OllamaConnectionError(OllamaError):
    pass


class OllamaModelError(OllamaError):
    pass


class OllamaClient:
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.timeout = settings.OLLAMA_REQUEST_TIMEOUT

    # ── チャット（同期） ──────────────────────────────────────────────
    def chat(self, model: str, messages: list, options: dict = None) -> dict:
        """
        Ollamaにチャットリクエストを送信して応答を返す。

        Args:
            model:    使用するモデル名 (例: "llama3.2")
            messages: OpenAI互換形式のメッセージリスト
                      [{"role": "user", "content": "..."}, ...]
            options:  モデルオプション (temperature, top_p など)

        Returns:
            {"content": str, "model": str, "done": bool}
        """
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": options or {},
        }
        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except requests.ConnectionError:
            raise OllamaConnectionError(
                f"Ollamaサーバーに接続できません: {self.base_url}"
            )
        except requests.HTTPError as e:
            if resp.status_code == 404:
                raise OllamaModelError(f"モデルが見つかりません: {model}")
            raise OllamaError(f"Ollamaエラー ({resp.status_code}): {resp.text}") from e

        data = resp.json()
        return {
            "content": data["message"]["content"],
            "model": data.get("model", model),
            "done": data.get("done", True),
            "eval_count": data.get("eval_count"),
            "prompt_eval_count": data.get("prompt_eval_count"),
        }

    # ── チャット（ストリーミング） ────────────────────────────────────
    def chat_stream(self, model: str, messages: list, options: dict = None):
        """
        ストリーミングでトークンをジェネレータとして返す。

        Yields:
            str  (テキストチャンク)
        """
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": options or {},
        }
        try:
            with requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=True,
                timeout=self.timeout,
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break
        except requests.ConnectionError:
            raise OllamaConnectionError(
                f"Ollamaサーバーに接続できません: {self.base_url}"
            )

    # ── モデル一覧 ────────────────────────────────────────────────────
    def list_models(self) -> list[dict]:
        """
        インストール済みモデルの一覧を返す。

        Returns:
            [{"name": str, "size": int, "modified_at": str}, ...]
        """
        try:
            resp = requests.get(
                f"{self.base_url}/api/tags",
                timeout=10,
            )
            resp.raise_for_status()
        except requests.ConnectionError:
            raise OllamaConnectionError(
                f"Ollamaサーバーに接続できません: {self.base_url}"
            )

        models = resp.json().get("models", [])
        return [
            {
                "name": m["name"],
                "size_gb": round(m.get("size", 0) / 1e9, 2),
                "modified_at": m.get("modified_at", ""),
            }
            for m in models
        ]


# シングルトンインスタンス（views.pyからインポートして使用）
ollama = OllamaClient()
