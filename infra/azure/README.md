# Azure Functions (Python) 開発・起動手順

1. Azure Functions Core Toolsのインストール

（Homebrew例／他は公式ガイド参照）

```bash
brew tap azure/functions
brew install azure-functions-core-tools@4
# or
npm i -g azure-functions-core-tools@4 --unsafe-perm true
```

2. プロジェクトディレクトリ作成 & 初期化

```bash
cd infra/azure     # 適宜、プロジェクト直下 or 作業ディレクトリ
func init . --python
```

• 既存プロジェクトに追加する場合はこのステップは省略可

3. Function 作成（例: HTTPトリガー）

```bash
func new --name function_app --template "HTTP trigger" --authlevel "function"
```

4. 依存ライブラリのインストール

• またはグローバル/venvでインストール

```bash
python3 -m venv .venv 
source .venv/bin/activate
pip install -r function_app/requirements.txt
```

```bash
pip install -r function_app/requirements.txt
```

5. local.settings.jsonの作成（環境変数セット）

• 必要な環境変数（APIキーやエンドポイント等）を function_app/local.settings.json か infra/azure/local.settings.jsonに記入
• 例:

```bash
{
  "IsEncrypted": false,
  "Values": {
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AZURE_OPENAI_ENDPOINT": "https://xxxx.openai.azure.com",
    "AZURE_OPENAI_API_KEY": "sk-...",
    "AZURE_OPENAI_DEPLOYMENT": "your-deployment-name",
    "AZURE_SEARCH_ENDPOINT": "https://xxxx.search.windows.net",
    "AZURE_SEARCH_API_KEY": "qn....",
    "AZURE_SEARCH_INDEX": "your-index-name"
  }
} 
```

6. ローカルで起動（HTTPサーバ起動）

```bash
func start
```

• http://localhost:7071/api/function_app でAPIが立ち上がる

• ログに「Function Runtime Version」や「[POST] http://localhost:7071/api/function_app」と表示されれば成功

7. curl等で動作確認

* request

```bash
curl -X POST "http://localhost:7071/api/function_app" \
-H "Content-Type: application/json" \
-d '{"query": "ここ1週間のクライミングのハイライトは？"}'
```

* response
  
```json
{"summary": "1週間のクライミングのハイライトは、昨日の岩壁での新しい課題に挑戦することでした。その課題は難しかったけれど、最終的にクリアすることができて、自分の成長を感じることができました。"}
```

[Azure公式ガイド](https://learn.microsoft.com/ja-jp/azure/azure-functions/functions-run-local) 参照