# Requirements Document

## Introduction

ByteSipは、毎日のIT/AIニュースを一口サイズで届けるAIエージェントです。エンジニアが朝のコーヒーを飲みながら、Qiita・Zenn・GitHubからその日のテック情報をキャッチアップできます。

本ドキュメントはMVP（必須機能）の要件を定義します。

## Requirements

### Requirement 1: ニュース提案

**Objective:** As a エンジニア, I want 今日のIT/AIニュースを一覧で確認したい, so that 効率的に最新技術情報をキャッチアップできる

#### Acceptance Criteria

1. When ユーザーが「今日のニュース教えて」とリクエストした時, the ByteSip Agent shall Qiita・Zenn・GitHubからニュースを取得して提案する
2. The ByteSip Agent shall 各ニュースについて以下の情報を提供する：タイトル（要約）、URL、内容要約、技術タグ配列
3. The ByteSip Agent shall 1回の提案で各サービス最大10件（合計30件）までのニュースを提案する
4. While キャッシュに90件（各サービス30件）のニュースが保持されている時, the ByteSip Agent shall キャッシュからニュースを取得する
5. When キャッシュのTTL（1日）が経過した時, the ByteSip Agent shall 外部APIから最新のニュースを再取得する

---

### Requirement 2: ソース指定フィルタ

**Objective:** As a エンジニア, I want 特定のソースからのニュースだけを見たい, so that 好みの情報源に集中できる

#### Acceptance Criteria

1. When ユーザーが「Qiitaのニュースだけ教えて」とリクエストした時, the ByteSip Agent shall Qiitaからのニュースのみを提案する
2. When ユーザーが「Zennだけ」とリクエストした時, the ByteSip Agent shall Zennからのニュースのみを提案する
3. When ユーザーが「GitHubだけ」とリクエストした時, the ByteSip Agent shall GitHubからのトレンドリポジトリのみを提案する

---

### Requirement 3: 件数指定

**Objective:** As a エンジニア, I want 取得するニュースの件数を指定したい, so that 時間に応じて適切な量の情報を得られる

#### Acceptance Criteria

1. When ユーザーが「3件だけ教えて」とリクエストした時, the ByteSip Agent shall 指定された件数のニュースを提案する
2. When ユーザーが「もっとたくさん」とリクエストした時, the ByteSip Agent shall より多くのニュースを提案する（上限: 各サービス10件、合計30件）
3. When ユーザーが「他のはある？」とリクエストした時, the ByteSip Agent shall キャッシュ内の未提案ニュースから追加で提案する
4. If キャッシュ内のすべてのニュースを提案済みの場合, the ByteSip Agent shall 「これ以上はありません」と応答する

---

### Requirement 4: 技術タグフィルタ

**Objective:** As a エンジニア, I want 特定の技術に関するニュースだけを見たい, so that 関心のある分野の情報を効率的に収集できる

#### Acceptance Criteria

1. When ユーザーが「Pythonに関するニュースだけ」とリクエストした時, the ByteSip Agent shall 技術タグにPythonを含むニュースのみを提案する
2. When ユーザーが「AIに関するものだけ」とリクエストした時, the ByteSip Agent shall AI関連の技術タグを含むニュースのみを提案する
3. The ByteSip Agent shall 技術タグによるフィルタリングをソース指定・件数指定と組み合わせて適用できる

---

### Requirement 5: 重複排除

**Objective:** As a エンジニア, I want 同じニュースを繰り返し見せられたくない, so that 常に新しい情報を効率的に取得できる

#### Acceptance Criteria

1. The ByteSip Agent shall STM（短期記憶）を使用して提案済みニュースを記憶する
2. When ユーザーが「ほかのニュースはある？」とリクエストした時, the ByteSip Agent shall STMに記録された提案済みニュースを除外して提案する
3. While 同一セッション内において, the ByteSip Agent shall 一度提案したニュースを再度提案しない

---

### Requirement 6: エラーハンドリング

**Objective:** As a エンジニア, I want エラー発生時に適切なフィードバックを受けたい, so that 問題の原因を理解できる

#### Acceptance Criteria

1. If 外部API（Qiita/Zenn/GitHub）への接続に失敗した場合, the ByteSip Agent shall エラーメッセージを返却する
2. If Rate Limitに達した場合, the ByteSip Agent shall 適切なエラーメッセージを返却する
3. While 一部のソースでエラーが発生している時, the ByteSip Agent shall 正常に取得できたソースからのニュースのみを提案する

---

## Out of Scope (MVP2)

以下の機能は本Specの対象外です：

- 期間指定（「今週のニュース」「直近3日」）
- 深掘り（「2番目の記事をもっと詳しく教えて」）
- ブックマーク（「これ後で読む」で保存）
- A2Aプロトコル対応
