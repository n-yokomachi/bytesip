# Implementation Plan

## Tasks

- [x] 1. プロジェクト基盤とインフラ構築
- [x] 1.1 Lambda プロジェクト初期化とデータモデル定義
  - Python 3.12 ベースの Lambda プロジェクト構造を作成
  - NewsItem、CacheEntry、FetchNewsRequest/Response などの共通データモデルを定義
  - ID 生成ルール（`{source}_{original_id}` 形式）を実装
  - 環境変数テンプレート（QIITA_ACCESS_TOKEN、GITHUB_ACCESS_TOKEN）を用意
  - _Requirements: 1.2_

- [x] 1.2 AWS CDK プロジェクト初期化
  - `infrastructure/cdk/` ディレクトリに CDK Python プロジェクトを作成
  - `cdk init app --language python` でプロジェクト初期化
  - 必要な依存関係（aws-cdk-lib, constructs）のセットアップ
  - _Requirements: 1.4, 1.5_

- [x] 1.3 CDK スタック実装（DynamoDB / Lambda）
  - `bytesip-news-cache` DynamoDB テーブル定義（PK: `SOURCE#<source>`, SK: `ITEM#<id>`）
  - TTL 属性の設定（24時間）
  - Lambda 関数定義（bytesip-news-fetcher）
  - SSM パラメータ参照（QIITA_ACCESS_TOKEN、GITHUB_ACCESS_TOKEN）
  - IAM ロールとポリシー設定
  - _Requirements: 1.4, 1.5_

- [x] 1.4 ローカル開発環境セットアップ
  - DynamoDB Local 用の docker-compose.yml（既存を活用）
  - テーブル作成スクリプトの更新
  - _Requirements: 1.4, 1.5_

---

- [ ] 2. キャッシュ管理機能
- [ ] 2.1 CacheManager 実装
  - ソース別にキャッシュエントリを取得する機能（TTL 確認含む）
  - ニュースアイテムをキャッシュに保存する機能（各ソース最大30件制限）
  - キャッシュ無効化機能
  - boto3 を使用した DynamoDB アクセス
  - _Requirements: 1.4, 1.5_

---

- [ ] 3. 外部ソースハンドラー
- [ ] 3.1 (P) QiitaHandler 実装
  - Qiita API v2 `/api/v2/items` からトレンド記事を取得
  - Bearer トークンによる認証処理
  - タグフィルタリング（query パラメータで `tag:python` 形式）
  - Rate Limit（1,000回/時）超過時のエラーハンドリング
  - body 冒頭 200 文字から要約を生成（Markdown をプレーンテキスト化）
  - _Requirements: 1.1, 4.1, 4.2, 6.1, 6.2_

- [ ] 3.2 (P) ZennHandler 実装
  - Zenn RSS フィード（`https://zenn.dev/feed`）をパース
  - feedparser ライブラリを使用した XML 処理
  - タグ指定時はトピック別 RSS（`/topics/{tag}/feed`）を使用
  - RSS の description フィールドから要約を抽出
  - パースエラー時のエラーハンドリング
  - _Requirements: 1.1, 4.1, 4.2, 6.1_

- [ ] 3.3 (P) GitHubHandler 実装
  - GitHub Search API `/search/repositories` からトレンドリポジトリを取得
  - `pushed:>YYYY-MM-DD stars:>100` クエリでトレンド代替
  - Personal Access Token による認証処理
  - Rate Limit（30回/分）超過時のエラーハンドリング
  - リポジトリの description フィールドから要約を抽出
  - _Requirements: 1.1, 6.1, 6.2_

---

- [ ] 4. ニュース取得オーケストレーション
- [ ] 4.1 NewsFetcher 並列取得実装
  - ThreadPoolExecutor（max_workers=3）による各ソースハンドラーの並列実行
  - キャッシュファースト戦略（キャッシュ確認 → API 呼び出し → キャッシュ更新）
  - ソース指定パラメータによるフィルタリング（未指定時は全ソース）
  - as_completed() による完了順の結果収集
  - _Requirements: 1.1, 1.4, 1.5_

- [ ] 4.2 Graceful Degradation 実装
  - 各ソースのエラーを SourceError として収集（接続エラー、Rate Limit、パースエラー）
  - 成功したソースの結果のみを返却
  - 全ソース失敗時は 503 エラーを返却
  - 部分的な成功時はエラー情報を含めてレスポンス
  - _Requirements: 6.1, 6.2, 6.3_

---

- [ ] 5. Strands Agent 実装
- [ ] 5.1 基本エージェント構成
  - Strands Agents SDK を使用したエージェント初期化
  - BedrockModel プロバイダーの設定
  - fetch_news ツールの定義と AgentCore Gateway への登録
  - _Requirements: 1.1_

- [ ] 5.2 AgentCore Memory STM 連携
  - AgentCore Memory の初期化とセッション管理
  - 提案済みニュース ID の取得機能（proposed_ids リスト）
  - 新規提案 ID の記録機能
  - セッション内での重複排除ロジック
  - _Requirements: 5.1, 5.2, 5.3_

- [ ] 5.3 フィルタリングと件数制御
  - ソース指定フィルタ（Qiita/Zenn/GitHub 個別指定）
  - 件数指定（ユーザー指定件数、上限各10件・合計30件）
  - 技術タグフィルタ（タグ名による絞り込み）
  - 追加提案リクエスト対応（「他のはある？」で未提案分を提案）
  - 在庫切れ時の応答（「これ以上はありません」）
  - _Requirements: 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3_

---

- [ ] 6. AgentCore デプロイメント
- [ ] 6.1 agentcore-starter-toolkit セットアップ
  - `pip install bedrock-agentcore-starter-toolkit` でツールキットをインストール
  - `agent/` ディレクトリにエージェントプロジェクトを作成
  - エージェントエントリポイント（bytesip_agent.py）の作成
  - _Requirements: 1.1_

- [ ] 6.2 AgentCore 設定とデプロイ
  - `agentcore configure -e bytesip_agent.py` でエージェント設定
  - AgentCore Memory (STM) の有効化
  - `agentcore deploy` でエージェントを AgentCore Runtime にデプロイ
  - `agentcore status` でデプロイ確認
  - _Requirements: 1.1, 5.1, 5.2, 5.3_

- [ ] 6.3 AgentCore Gateway 統合
  - Lambda 関数を AgentCore Gateway に登録
  - fetch_news ツールの MCP 定義
  - Gateway 経由での Lambda 呼び出しテスト
  - _Requirements: 1.1_

---

- [ ] 7. Streamlit UI
- [ ] 7.1 Streamlit UI 実装
  - チャットインターフェースの構築
  - ユーザーメッセージの送信とエージェントレスポンスの表示
  - ニュース一覧の整形表示（タイトル、URL、要約、タグ）
  - エラーメッセージの表示
  - _Requirements: 1.2, 1.3_

---

- [ ] 8. テスト
- [ ] 8.1 (P) 単体テスト
  - CacheManager: TTL 有効/切れ、30件上限、無効化
  - QiitaHandler: 正常取得、Rate Limit エラー、タグフィルタ
  - ZennHandler: RSS パース成功、bozo エラー、トピック別 RSS
  - GitHubHandler: 正常取得、Rate Limit エラー
  - _Requirements: 1.4, 1.5, 6.1, 6.2_

- [ ] 8.2 (P) 統合テスト
  - NewsFetcher → CacheManager → DynamoDB 連携
  - 並列取得の動作確認
  - AgentCore Gateway → Lambda 呼び出し
  - STM への提案済み ID 記録・取得
  - _Requirements: 1.1, 1.4, 5.1, 5.2_

- [ ] 8.3 E2E テスト
  - Streamlit → Agent → Lambda → 外部 API の全フロー
  - ソース指定フィルタの動作確認
  - 件数指定の動作確認
  - 技術タグフィルタの動作確認
  - 「他のはある？」での追加提案と重複排除
  - _Requirements: 1.1, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3, 5.1, 5.2, 5.3_

---

## Requirements Coverage

| Requirement | Tasks |
|-------------|-------|
| 1.1 | 3.1, 3.2, 3.3, 4.1, 5.1, 6.1, 6.2, 6.3, 8.2, 8.3 |
| 1.2 | 1.1, 7.1 |
| 1.3 | 5.3, 7.1 |
| 1.4 | 1.2, 1.3, 1.4, 2.1, 4.1, 8.1, 8.2 |
| 1.5 | 1.2, 1.3, 1.4, 2.1, 4.1, 8.1 |
| 2.1, 2.2, 2.3 | 5.3, 8.3 |
| 3.1, 3.2, 3.3, 3.4 | 5.3, 8.3 |
| 4.1, 4.2, 4.3 | 3.1, 3.2, 5.3, 8.3 |
| 5.1, 5.2, 5.3 | 5.2, 6.2, 8.2, 8.3 |
| 6.1, 6.2, 6.3 | 3.1, 3.2, 3.3, 4.2, 8.1 |
