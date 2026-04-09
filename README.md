# Django + Ollama REST API

ローカル / イントラネット向けの LLM REST API サーバーです。
APIキーは不要で、`ALLOWED_HOSTS` によるIP制限でアクセスを管理します。

---

## ディレクトリ構成

```
django_ollama_api/
├── config/
│   ├── __init__.py
│   ├── settings.py     # 設定 (ALLOWED_HOSTS, OLLAMA_BASE_URL など)
│   ├── urls.py         # ルートURL
│   └── wsgi.py
├── llm_api/
│   ├── __init__.py
│   ├── ollama_client.py  # Ollama HTTP通信ラッパー
│   ├── serializers.py    # 入出力バリデーション
│   ├── views.py          # APIエンドポイント
│   └── urls.py
├── .env.example
├── manage.py
└── requirements.txt
```

---

## セットアップ手順

### 1. Ollama のインストール・起動

```bash
# インストール (Linux/Mac)
curl -fsSL https://ollama.com/install.sh | sh

# モデルをダウンロード
ollama pull llama3.2

# Ollamaサーバー起動 (デフォルト: localhost:11434)
ollama serve
```

### 2. Python 環境の準備

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 環境変数の設定

```bash
cp .env.example .env
# .env を編集して ALLOWED_HOSTS などを設定
```

`.env` の主な設定項目:

| 変数名 | 説明 | 例 |
|---|---|---|
| `DJANGO_SECRET_KEY` | Djangoシークレットキー | ランダムな文字列 |
| `ALLOWED_HOSTS` | 許可するIPアドレス (カンマ区切り) | `192.168.1.10,192.168.1.20` |
| `OLLAMA_BASE_URL` | OllamaサーバーのURL | `http://localhost:11434` |
| `OLLAMA_DEFAULT_MODEL` | デフォルトモデル | `llama3.2` |
| `THROTTLE_RATE` | レート制限 | `30/minute` |

### 4. 開発サーバー起動

```bash
python manage.py runserver 0.0.0.0:8000
```

### 5. 本番環境 (Gunicorn + Nginx)

```bash
pip install gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

---

## API エンドポイント

### `POST /api/chat/` — チャット (同期)

```json
// リクエスト
{
  "model": "llama3.2",
  "messages": [
    {"role": "system", "content": "あなたは親切なアシスタントです。"},
    {"role": "user",   "content": "Pythonとは何ですか？"}
  ],
  "temperature": 0.7,
  "top_p": 0.9
}

// レスポンス
{
  "model": "llama3.2",
  "content": "Pythonは汎用プログラミング言語で...",
  "done": true,
  "eval_count": 120,
  "prompt_eval_count": 30
}
```

### `POST /api/chat/stream/` — チャット (SSEストリーミング)

レスポンスは `text/event-stream` 形式:

```
data: {"token": "Python"}
data: {"token": "は"}
data: {"token": "汎用"}
...
data: {"done": true}
```

### `GET /api/models/` — モデル一覧

```json
{
  "models": [
    {"name": "llama3.2:latest", "size_gb": 2.02, "modified_at": "2024-..."}
  ]
}
```

### `GET /api/health/` — ヘルスチェック

```json
{"django": "ok", "ollama": "ok", "model_count": 3}
```

---

## VB.NET からの呼び出し例

```vb
Imports System.Net.Http
Imports System.Text
Imports Newtonsoft.Json  ' NuGet: Newtonsoft.Json

Public Class OllamaApiClient
    Private ReadOnly _httpClient As New HttpClient()
    Private ReadOnly _baseUrl As String = "http://your-server:8000"

    Public Async Function ChatAsync(userMessage As String,
                                    Optional model As String = "llama3.2") As Task(Of String)
        Dim requestBody = New With {
            .model = model,
            .messages = New Object() {
                New With {.role = "user", .content = userMessage}
            }
        }

        Dim json = JsonConvert.SerializeObject(requestBody)
        Dim content = New StringContent(json, Encoding.UTF8, "application/json")

        Dim response = Await _httpClient.PostAsync($"{_baseUrl}/api/chat/", content)
        response.EnsureSuccessStatusCode()

        Dim responseJson = Await response.Content.ReadAsStringAsync()
        Dim result = JsonConvert.DeserializeObject(Of Dictionary(Of String, Object))(responseJson)
        Return result("content").ToString()
    End Function
End Class
```

---

## curl での動作確認

```bash
# ヘルスチェック
curl http://localhost:8000/api/health/

# チャット
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "こんにちは"}]}'

# モデル一覧
curl http://localhost:8000/api/models/
```
