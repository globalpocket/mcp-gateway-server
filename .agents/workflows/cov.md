# Coverage Check Workflow

このワークフローは、テストを実行し、カバレッジレポート（HTML）を生成します。

## Steps

1. カバレッジ測定付きテストの実行
   ```bash
   PYTHONPATH=src pytest --cov=src/mcp_gateway --cov-report=html tests/
   ```
