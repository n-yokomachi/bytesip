# Research & Design Decisions

## Summary
- **Feature**: `bytesip-news-agent`
- **Discovery Scope**: New Feature (greenfield)
- **Key Findings**:
  - Strands Agents SDK は Python 3.10+ 必須、BedrockModel がデフォルトプロバイダー
  - AgentCore Memory は STM/LTM を提供、LTM はバックグラウンドで非同期抽出
  - Qiita API は認証トークン使用時 1,000回/時のRate Limit

## Research Log

### Strands Agents SDK
- **Context**: エージェントフレームワークの選定確認
- **Sources Consulted**:
  - [GitHub - strands-agents/sdk-python](https://github.com/strands-agents/sdk-python)
  - [Strands Agents 公式ドキュメント](https://strandsagents.com/latest/)
  - [AWS Open Source Blog](https://aws.amazon.com/blogs/opensource/introducing-strands-agents-an-open-source-ai-agents-sdk/)
- **Findings**:
  - Python 3.10+ 必須
  - BedrockModel がデフォルト、Claude Sonnet 4.5 を使用
  - MCP (Model Context Protocol) ビルトインサポート
  - boto3 を使用して Bedrock と通信
  - Multi-agent システム、ストリーミング対応
- **Implications**: Python 3.10+ 環境が前提。Tool 定義は MCP 形式で統一可能

### Amazon Bedrock AgentCore
- **Context**: インフラ基盤の仕様確認
- **Sources Consulted**:
  - [Amazon Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/)
  - [AgentCore Memory - Strands Agents](https://strandsagents.com/latest/documentation/docs/community/session-managers/agentcore-memory/)
  - [DEV Community - AgentCore Memory](https://dev.to/aws-heroes/amazon-bedrock-agentcore-runtime-part-7-using-agentcore-long-term-memory-with-strands-agents-sdk-lb2)
- **Findings**:
  - **Runtime**: サーバーレスでエージェントをデプロイ・スケール
  - **Gateway**: API/Lambda を agent-ready なツールに変換
  - **Memory**:
    - STM: 会話の即座の持続性
    - LTM: preferences、facts、summaries を非同期抽出
    - STM_AND_LTM 戦略で両方を有効化
    - プロビジョニングに 2-5 分かかる
  - 従量課金制、最低料金なし
- **Implications**:
  - Gateway 経由で Lambda をツールとして登録
  - STM で提案済みニュース ID を記録し重複排除を実現
  - LTM は MVP では使用せず（ユーザー嗜好学習は MVP2）

### Qiita API v2
- **Context**: 外部 API の仕様確認
- **Sources Consulted**:
  - [Qiita API v2 documentation](https://qiita.com/api/v2/docs)
- **Findings**:
  - エンドポイント: `GET /api/v2/items`
  - 認証: Bearer トークン (`Authorization: Bearer {token}`)
  - Rate Limit: 認証済み 1,000回/時、未認証 60回/時
  - ページネーション: `page`, `per_page` パラメータ
  - タグフィルタ: `query` パラメータで `tag:python` 形式
- **Implications**: 認証トークン必須（Rate Limit 対策）。環境変数で管理

### Zenn RSS
- **Context**: RSS フィード仕様の確認
- **Sources Consulted**:
  - [Zenn RSS フィード](https://zenn.dev/zenn/articles/zenn-feed-rss)
  - 実際の RSS フィード (`https://zenn.dev/feed`) を検証
- **Findings**:
  - トレンド: `https://zenn.dev/feed`
  - トピック別: `https://zenn.dev/topics/{topicname}/feed`
  - 明示的な Rate Limit なし
  - XML 形式（RSS 2.0）
  - **重要**: category タグは存在しない（tech/idea の区別なし）
  - **重要**: トピック（技術タグ）情報は RSS に含まれない
  - description: 記事冒頭のテキストが自動抽出される
- **Implications**:
  - `feedparser` ライブラリで XML パース
  - タグフィルタリングはトピック別 RSS で代替（`/topics/{tag}/feed`）
  - トレンド RSS 使用時は `NewsItem.tags = []` となる

### GitHub Search API
- **Context**: トレンドリポジトリ取得方法の確認
- **Sources Consulted**:
  - [GitHub REST API - Search](https://docs.github.com/en/rest/search)
- **Findings**:
  - エンドポイント: `GET /search/repositories`
  - Rate Limit: 30回/分（認証済み）
  - トレンド代替クエリ: `pushed:>YYYY-MM-DD stars:>100`
  - 公式トレンド API は存在しない
- **Implications**: クエリパラメータで「最近更新 + 高Star」を代替実装

### bedrock-agentcore-starter-toolkit
- **Context**: AgentCore へのエージェントデプロイ方法
- **Sources Consulted**:
  - [GitHub - aws/bedrock-agentcore-starter-toolkit](https://github.com/aws/bedrock-agentcore-starter-toolkit)
  - [AgentCore Starter Toolkit Documentation](https://aws.github.io/bedrock-agentcore-starter-toolkit/)
- **Findings**:
  - CLI ツールでエージェントを AgentCore Runtime にデプロイ
  - インストール: `pip install bedrock-agentcore-starter-toolkit`
  - 主要コマンド:
    - `agentcore create` - プロジェクトスキャフォールド
    - `agentcore configure -e my_agent.py` - エージェント設定
    - `agentcore deploy` - デプロイ（Direct Code Deploy がデフォルト）
    - `agentcore status` - ステータス確認
    - `agentcore invoke '{"prompt": "..."}'` - テスト実行
    - `agentcore destroy` - クリーンアップ
  - デプロイモード:
    - Direct Code Deploy（デフォルト）: ローカル Docker 不要
    - Local Development: `--local` フラグ
    - Hybrid Build: `--local-build` フラグ
  - AgentCore Memory, Gateway, Code Interpreter 等の統合サポート
  - Strands Agents, LangGraph, CrewAI 等のフレームワークに対応
- **Implications**:
  - インフラ管理なしでエージェントをデプロイ可能
  - AgentCore Gateway で Lambda をツールとして登録
  - AgentCore Memory (STM) でセッション管理

## Architecture Pattern Evaluation

| Option | Description | Strengths | Risks / Limitations | Notes |
|--------|-------------|-----------|---------------------|-------|
| Modular Monolith | Lambda 内でハンドラーをモジュール分割 | シンプル、デプロイ容易 | スケール時に分割が必要 | MVP に最適 |
| Microservices | 各ソースを個別 Lambda に分割 | 独立スケール、障害分離 | 複雑性増、コールドスタート増加 | Over-engineering for MVP |
| Event-driven | SQS/SNS でソース間を非同期連携 | 疎結合、再試行容易 | 複雑性増、レイテンシ増加 | 将来のスケール時に検討 |

**選択**: Modular Monolith（単一 Lambda + モジュール分割）

## Design Decisions

### Decision: 単一 Lambda 関数でのマルチソース対応
- **Context**: 3 つの外部ソース（Qiita/Zenn/GitHub）をどう統合するか
- **Alternatives Considered**:
  1. 各ソースを個別 Lambda に分割
  2. 単一 Lambda 内でハンドラー分岐
- **Selected Approach**: 単一 Lambda 内でハンドラーモジュールを分割
- **Rationale**: MVP ではシンプルさを優先。1 つの Lambda で管理できる規模
- **Trade-offs**: 1 ソースの障害が全体に影響する可能性 → try-except で分離
- **Follow-up**: 将来的にソース追加時は分割を再検討

### Decision: DynamoDB シングルテーブル設計
- **Context**: キャッシュデータの格納方法
- **Alternatives Considered**:
  1. ソース別にテーブルを分ける
  2. シングルテーブルで PK にソース名を含める
- **Selected Approach**: シングルテーブル（PK: `SOURCE#<source_name>`, SK: `ITEM#<item_id>`）
- **Rationale**: DynamoDB のベストプラクティスに従い、クエリ効率を最大化
- **Trade-offs**: スキーマ設計の学習コスト
- **Follow-up**: アクセスパターンに応じて GSI を追加

### Decision: STM による重複排除
- **Context**: 提案済みニュースをセッション内で記憶する方法
- **Alternatives Considered**:
  1. Lambda 側で DynamoDB にセッション情報を保存
  2. AgentCore STM を使用
- **Selected Approach**: AgentCore STM を使用
- **Rationale**: Strands Agents + AgentCore の統合を活用。追加インフラ不要
- **Trade-offs**: AgentCore Memory の仕様に依存
- **Follow-up**: STM への書き込み形式（提案済み ID リスト）を実装時に決定

### Decision: 並列 API 呼び出し
- **Context**: 3 つの外部ソースからのデータ取得を効率化する方法
- **Alternatives Considered**:
  1. 順次実行（シンプルだが遅い）
  2. `asyncio` による非同期実行
  3. `concurrent.futures.ThreadPoolExecutor` による並列実行
- **Selected Approach**: `ThreadPoolExecutor(max_workers=3)` で並列実行
- **Rationale**:
  - 外部 API 呼び出しは I/O バウンドのためスレッド並列が有効
  - `asyncio` は既存ライブラリ（requests, feedparser）との互換性で複雑化
  - ThreadPoolExecutor は標準ライブラリで追加依存なし
- **Trade-offs**: スレッド数は固定（3）だが、ソース数と一致するため問題なし
- **Follow-up**: 将来ソース追加時は max_workers を調整

### Decision: AWS CDK でのインフラ構築
- **Context**: Lambda / DynamoDB 等の AWS リソースをどのように管理するか
- **Alternatives Considered**:
  1. AWS SAM (Serverless Application Model)
  2. AWS CDK (Cloud Development Kit)
  3. Terraform
- **Selected Approach**: AWS CDK (Python)
- **Rationale**:
  - プロジェクトが Python ベースのため、CDK Python も自然な選択
  - SAM より柔軟性が高く、複雑なリソース構成に対応可能
  - CDK は L2 Construct で簡潔に記述可能
  - 将来の拡張（Step Functions, EventBridge 等）にも対応しやすい
- **Trade-offs**: SAM より学習コストがやや高い
- **Follow-up**: CDK スタック構成（単一スタック vs 複数スタック）は MVP では単一で開始

### Decision: agentcore-starter-toolkit でのエージェントデプロイ
- **Context**: Strands Agent を AgentCore Runtime にどのようにデプロイするか
- **Alternatives Considered**:
  1. CDK で AgentCore Runtime リソースを直接定義
  2. agentcore-starter-toolkit CLI を使用
  3. AWS Console からマニュアル設定
- **Selected Approach**: agentcore-starter-toolkit CLI
- **Rationale**:
  - 公式ツールで AgentCore に最適化されている
  - `agentcore deploy` 一発でデプロイ完了
  - AgentCore Memory, Gateway との統合がビルトイン
  - Direct Code Deploy モードで Docker 不要
- **Trade-offs**: CDK との二重管理になるが、責務分離が明確
  - CDK: 永続リソース（DynamoDB, Lambda, SSM）
  - agentcore-starter-toolkit: エージェント実行環境
- **Follow-up**: CI/CD パイプラインでの統合方法を検討

## Risks & Mitigations
- **Rate Limit 超過**: Qiita/GitHub の Rate Limit 超過 → キャッシュで API 呼び出しを最小化（TTL: 1日）
- **外部 API 障害**: 1 つのソースがダウン → 他のソースからのニュースのみ返却（Graceful Degradation）
- **コールドスタート**: Lambda 初回起動遅延 → Provisioned Concurrency は MVP では不要（許容範囲）
- **Memory プロビジョニング遅延**: AgentCore Memory は初回 2-5 分かかる → 事前プロビジョニング

## References
- [Strands Agents SDK - GitHub](https://github.com/strands-agents/sdk-python)
- [Amazon Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/)
- [Qiita API v2 documentation](https://qiita.com/api/v2/docs)
- [Zenn RSS フィード](https://zenn.dev/zenn/articles/zenn-feed-rss)
- [GitHub REST API - Search](https://docs.github.com/en/rest/search)
