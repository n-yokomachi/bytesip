# ByteSip AgentCore + Lambda 統合トラブルシューティング

このドキュメントは、ByteSip エージェントを AWS Bedrock AgentCore にデプロイし、Lambda 関数と連携させる際に遭遇した問題とその解決策をまとめたものです。

## 概要

ByteSip は以下のアーキテクチャで構成されています：

```
Streamlit UI → AgentCore Runtime (エージェント) → Lambda (ニュース取得) → DynamoDB (キャッシュ)
                                                 ↓
                                            外部 API (Qiita, Zenn, GitHub)
```

## 発生した問題と解決策

### 問題 1: Lambda の相対インポートエラー

**症状:**
```
Unable to import module 'handler': attempted relative import with no known parent package
```

**原因:**
Lambda のハンドラーコードで相対インポート (`from .models import ...`) を使用していたが、Lambda 実行環境ではパッケージとして認識されない。

**解決策:**
すべての Python モジュールで try/except を使用して相対・絶対インポートの両方に対応：

```python
# Support both relative imports (local) and package imports (Lambda)
try:
    from .models import NewsItem, SourceError
    from .handlers.base import BaseHandler
except ImportError:
    from models import NewsItem, SourceError
    from handlers.base import BaseHandler
```

**修正ファイル:**
- `infrastructure/lambda/bytesip_news_fetcher/handler.py`
- `infrastructure/lambda/bytesip_news_fetcher/cache_manager.py`
- `infrastructure/lambda/bytesip_news_fetcher/news_fetcher.py`
- `infrastructure/lambda/bytesip_news_fetcher/handlers/base.py`
- `infrastructure/lambda/bytesip_news_fetcher/handlers/qiita.py`
- `infrastructure/lambda/bytesip_news_fetcher/handlers/zenn.py`
- `infrastructure/lambda/bytesip_news_fetcher/handlers/github.py`

---

### 問題 2: Lambda で Python パッケージが見つからない

**症状:**
```
Unable to import module 'handler': No module named 'requests'
```

**原因:**
Lambda 実行環境には `requests` や `feedparser` がプリインストールされていない。

**解決策:**
CDK の Lambda 定義でバンドリングを設定し、依存関係を含める：

```typescript
// infrastructure/cdk/lib/bytesip-stack.ts
code: lambda.Code.fromAsset(lambdaBasePath, {
  bundling: {
    image: lambda.Runtime.PYTHON_3_12.bundlingImage,
    command: [
      "bash",
      "-c",
      [
        "pip install requests feedparser -t /asset-output",
        "cp -r bytesip_news_fetcher/* /asset-output/",
      ].join(" && "),
    ],
  },
}),
```

---

### 問題 3: CDK デプロイ時の Secrets Manager エラー

**症状:**
```
Value at 'secretString' failed to satisfy constraint: Member must have length greater than or equal to 1
```

**原因:**
環境変数 `QIITA_ACCESS_TOKEN` と `GITHUB_ACCESS_TOKEN` が設定されていない場合、空文字列でシークレットを更新しようとしてエラーになる。

**解決策:**
環境変数が設定されている場合のみシークレットを作成/更新するように条件分岐：

```typescript
const qiitaToken = process.env.QIITA_ACCESS_TOKEN;

if (qiitaToken) {
  const qiitaCfnSecret = new secretsmanager.CfnSecret(
    this,
    "QiitaAccessToken",
    {
      name: qiitaSecretName,
      secretString: qiitaToken,
    }
  );
}

// 既存のシークレットを参照（存在することを前提）
const qiitaSecret = secretsmanager.Secret.fromSecretNameV2(
  this,
  "QiitaSecretRef",
  qiitaSecretName
);
```

---

### 問題 4: AgentCore Runtime でのメモリアクセスエラー

**症状:**
```
AccessDeniedException: User is not authorized to perform: bedrock-agentcore:ListMemories
```

**原因:**
`AGENTCORE_MEMORY_ID` 環境変数が設定されていない場合、コードがメモリ一覧を取得しようとするが、Runtime の IAM ロールにはその権限がない。

**解決策:**
`entrypoint.py` でメモリ ID のフォールバック値を設定：

```python
# Memory ID from toolkit deployment (set by agentcore deploy)
# Fallback to known memory ID if not provided
AGENTCORE_MEMORY_ID = os.environ.get("AGENTCORE_MEMORY_ID", "bytesip_mem-Y05j1y8kDc")
```

**注意:** メモリ ID は `agentcore deploy` の出力で確認できます：
```
Using existing memory: bytesip_mem-Y05j1y8kDc
```

---

### 問題 5: エージェントから Lambda を呼び出せない（リージョンエラー）

**症状:**
```
リージョン設定エラーが発生しており、ニュース取得ができない状態です
```

**原因:**
`boto3.client("lambda")` でリージョンが指定されていないため、Lambda クライアントの初期化に失敗。

**解決策:**
`tools.py` の `_get_default_client()` でリージョンを明示的に指定：

```python
def _get_default_client() -> FetchNewsClient:
    global _default_client
    if _default_client is None:
        import os
        import boto3

        region = os.environ.get("AWS_REGION", "ap-northeast-1")
        env = os.environ.get("BYTESIP_ENVIRONMENT", "development")
        function_name = f"bytesip-news-fetcher-{env}"

        lambda_client = boto3.client("lambda", region_name=region)
        _default_client = FetchNewsClient(
            lambda_client=lambda_client,
            function_name=function_name,
        )
    return _default_client
```

---

### 問題 6: エージェントから Lambda を呼び出せない（権限エラー）

**症状:**
```
Lambda関数へのアクセス権限がない状態です
```

**原因:**
AgentCore Runtime の IAM ロールに Lambda 関数を呼び出す権限がない。

**解決策:**

1. **Lambda リソースポリシーを追加:**
```bash
aws lambda add-permission \
  --function-name bytesip-news-fetcher-development \
  --statement-id AgentCoreRuntimeInvoke \
  --action lambda:InvokeFunction \
  --principal bedrock-agentcore.amazonaws.com \
  --source-arn "arn:aws:bedrock-agentcore:ap-northeast-1:765653276628:runtime/*" \
  --region ap-northeast-1
```

2. **IAM ロールにポリシーをアタッチ:**
```bash
aws iam attach-role-policy \
  --role-name AmazonBedrockAgentCoreSDKRuntime-ap-northeast-1-4f761cb595 \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaRole \
  --region ap-northeast-1
```

**注意:** IAM ポリシーの反映には数分かかる場合があります。

---

### 問題 7: Qiita/GitHub からデータ取得できない（シークレット読み取りエラー）

**症状:**
```
Zenn のデータのみ取得でき、Qiita と GitHub のデータが取得できない
```

**原因:**
1. Secrets Manager のシークレットが存在しない（CDK 再デプロイ時に削除された可能性）
2. Lambda の `config.py` でシークレット取得時のエラーが握りつぶされている

**解決策:**

1. **シークレットの存在確認:**
```bash
aws secretsmanager get-secret-value \
  --secret-id "bytesip/development/qiita-access-token" \
  --region ap-northeast-1

aws secretsmanager get-secret-value \
  --secret-id "bytesip/development/github-access-token" \
  --region ap-northeast-1
```

2. **シークレットが存在しない場合は再作成:**
```bash
aws secretsmanager create-secret \
  --name "bytesip/development/qiita-access-token" \
  --secret-string "$QIITA_ACCESS_TOKEN" \
  --region ap-northeast-1

aws secretsmanager create-secret \
  --name "bytesip/development/github-access-token" \
  --secret-string "$GITHUB_ACCESS_TOKEN" \
  --region ap-northeast-1
```

3. **Lambda の `config.py` にデバッグログを追加:**
```python
@lru_cache(maxsize=10)
def _get_secret(secret_name: str) -> str | None:
    import logging
    logger = logging.getLogger(__name__)

    region = os.getenv("AWS_REGION", "")
    logger.info(f"Getting secret: {secret_name}, AWS_REGION={region}")

    if not region:
        logger.error("AWS_REGION is not set")
        return None

    client = boto3.client("secretsmanager", region_name=region)
    try:
        response = client.get_secret_value(SecretId=secret_name)
        secret_value = response.get("SecretString")
        if secret_value:
            logger.info(f"Successfully retrieved secret: {secret_name}")
        return secret_value
    except ClientError as e:
        logger.error(f"Failed to get secret {secret_name}: {e}")
        return None
```

**注意:**
- Lambda ランタイムは `AWS_REGION` を自動設定するため、CDK で手動設定は不要（予約済み変数エラーになる）
- CDK で条件付きシークレット作成を行う場合、環境変数未設定時に既存シークレットが削除されることがある

---

## デバッグ方法

### CloudWatch ログの確認

```bash
# リアルタイムでログを追跡
aws logs tail /aws/bedrock-agentcore/runtimes/bytesip-BzLD5m92MA-DEFAULT \
  --log-stream-name-prefix "2026/02/03/[runtime-logs" --follow

# 過去1時間のログを確認
aws logs tail /aws/bedrock-agentcore/runtimes/bytesip-BzLD5m92MA-DEFAULT \
  --log-stream-name-prefix "2026/02/03/[runtime-logs" --since 1h
```

### エージェントのテスト

```bash
# agentcore CLI でテスト
cd agent
uv run agentcore invoke '{"prompt": "今日のニュースを教えて"}'
```

### Gateway のテスト

```bash
# Gateway 経由でテスト
cd agent
uv run python ../scripts/test_gateway.py
```

---

## 環境変数

### エージェント (entrypoint.py)
| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| `AWS_REGION` | AWS リージョン | `ap-northeast-1` |
| `BYTESIP_MEMORY_NAME` | メモリ名 | `bytesip_mem` |
| `AGENTCORE_MEMORY_ID` | メモリ ID | `bytesip_mem-Y05j1y8kDc` |

### ツール (tools.py)
| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| `AWS_REGION` | AWS リージョン | `ap-northeast-1` |
| `BYTESIP_ENVIRONMENT` | 環境名 | `development` |

### Lambda (handler.py)
| 変数名 | 説明 | 備考 |
|--------|------|------|
| `DYNAMODB_TABLE_NAME` | DynamoDB テーブル名 | CDK で設定 |
| `QIITA_SECRET_NAME` | Qiita トークンのシークレット名 | CDK で設定 |
| `GITHUB_SECRET_NAME` | GitHub トークンのシークレット名 | CDK で設定 |
| `AWS_REGION` | AWS リージョン | Lambda 実行環境で自動設定 |

---

## チェックリスト

デプロイ後に問題が発生した場合のチェックリスト：

- [ ] CDK デプロイが成功しているか
- [ ] Lambda 関数が正しいコードでデプロイされているか
- [ ] エージェントが再デプロイされているか (`agentcore deploy`)
- [ ] Lambda のリソースポリシーが設定されているか
- [ ] IAM ロールに Lambda 呼び出し権限があるか
- [ ] CloudWatch ログでエラーを確認したか
- [ ] メモリ ID が正しく設定されているか
- [ ] Secrets Manager にシークレットが存在するか
