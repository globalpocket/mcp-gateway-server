# 📖 MCP Routing Gateway - ユーザーマニュアル

## 1. はじめに

**MCP Routing Gateway** は、AIエージェント（Cline、Claude Desktop、Brownieなど）と underlying infrastructure（バックエンドのインフラ）の複雑さを完全に分離するために設計された、純粋でステートレスなルーティングプロキシおよびファサードレイヤーです。

AIエージェントに対しては、本ゲートウェイが**「単一のインテリジェントなMCPサーバー」**として振る舞います。標準の `stdio` (標準入出力) を介した通信を透過的に多重化し、HTTP/SSEを経由して複数のバックエンドMCPサーバーへルーティングを行うと同時に、AIが使用できるツールを厳格に管理・制御します。

## 2. 主な機能

* **ゼロ・ペイロード干渉 (Pure Proxy):** `tools/call` リクエストを転送する際、ルーティングのためにツール名のみを書き換えますが、IDや引数などのペイロードは一切変更せずに透過させます。
* **ツールのフィルタリングと仮想化 (Facade Pattern):** ブロックリスト（後述）を使用して特定のツールをAIから完全に隠蔽したり、安全にラップされた「仮想ツール」を提供したりできます。
* **スマートな名前空間解決:** 複数のサーバー間でツール名が競合した場合、プレフィックス付きエイリアス（例: `serverA_read_file`）とベース名の両方を提供します。設定により特定のサーバーへ固定する決定的なルーティングも可能です。
* **全二重マルチプレクサとID衝突回避:** 永続的なSSEストリームを維持し、バックエンドからLLMへの逆方向リクエスト（`sampling` 等）を完全にサポートします。複数サーバー間でリクエストIDが重複した場合でも、ゲートウェイ内で一意のIDにすり替えてルーティングの破綻を防ぎます。
* **厳格なMCPプロトコル準拠:** 初期化ハンドシェイク (`initialize`)、死活監視の `ping`、および時間のかかるタスクを中断するための `notifications/cancelled` を完全にサポートしています。

## 3. インストール

本プロジェクトは Python 3.10 以上を必要とします。

```bash
# 1. 仮想環境の作成と有効化
python3 -m venv .venv
source .venv/bin/activate

# 2. パッケージのインストール
pip install -e .
```

## 4. 設定 (`gateway_config.yaml`)

ゲートウェイの動作は YAML 設定ファイルで定義します。

```yaml
version: "1.0"

# 1. 仮想ツール (Facade)
# 特定のバックエンドルートに安全にマッピングされる抽象的なツールを定義
virtual_tools:
  run_command:
    description: "安全なサンドボックス内でシェルコマンドを実行します。"
    target_route: "/mcp/sandbox"

# 2. 明示的なルーティング (優先度: 最高)
# 名前が衝突した場合に、ベースツール名を特定のサーバーに固定
explicit_routing:
  read_file: "serverA"
  search_github: "serverB"

# 3. ブロックツール (明示的フィルタリング)
# 特定のツールをAIエージェントから完全に隠蔽（Hide）
blocked_tools:
  - "search_github"         # ベース名をブロック
  - "serverA_run_command"   # プレフィックス付きの名前をブロック
```

## 5. 使い方

### ゲートウェイの起動

CLI を使用してゲートウェイを起動します。デフォルトでは実行ディレクトリの `gateway_config.yaml` を読み込みます。

```bash
# 基本的な起動
mcp-gateway

# カスタム設定ファイルを指定
mcp-gateway --config custom_config.yaml

# バックエンドのベースURLを上書き (デフォルトは http://localhost:8000)
MCP_BACKEND_BASE_URL="http://mcp-router.local" mcp-gateway
```
*注: ゲートウェイはAIエージェントと `stdio` で通信します。JSON-RPCのペイロードを汚染しないよう、ログはすべて `stderr` に出力されます。*

### Control Plane API (管理用インターフェース)

ゲートウェイは `http://127.0.0.1:8001` で REST API を公開しており、動的なプロビジョニングが可能です。

* **バックエンドサーバーの動的追加・同期:**
    指定したルートに接続し、`initialize` ハンドシェイクを経てツール一覧を取得・結合します。

```bash
curl -X POST http://127.0.0.1:8001/admin/routes/sync \
     -H "Content-Type: application/json" \
     -d '{"server_name": "serverA", "target_route": "/mcp/serverA"}'
```

* **バックエンドサーバーの削除:**
    レジストリからサーバーを削除し、リソースリークを防ぐために該当サーバーへのSSE接続タスクを安全にキャンセルします。

```bash
curl -X DELETE http://127.0.0.1:8001/admin/routes/serverA
```

## 6. AIエージェントとの統合

Claude Desktop や Cline で本ゲートウェイを使用するには、設定ファイルに標準的な `stdio` MCPサーバーとして登録してください。

**設定例 (Claude Desktop):**

```json
{
  "mcpServers": {
    "mcp-routing-gateway": {
      "command": "mcp-gateway",
      "args": ["--config", "/absolute/path/to/gateway_config.yaml"],
      "env": {
        "MCP_BACKEND_BASE_URL": "http://localhost:8000"
      }
    }
  }
}
```
