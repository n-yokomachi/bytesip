---
name: commit
description: 変更をコミットする。git commit、変更を保存する場合に使用。
allowed-tools: Bash
---

# コミットスキル

現在の変更をコミットします。

## 実行手順

1. **状態確認**

   ```bash
   git status
   git diff --stat
   ```

2. **変更をステージング**

   ```bash
   git add .
   ```

3. **コミット作成**
   ```bash
   git commit -m "コミットメッセージ"
   ```

## コミットメッセージのルール

- 日本語で記述
- Conventional Commitsの接頭辞を使用（feat:, fix:, docs:, refactor: など）
- 簡潔に変更内容を説明

## 禁止事項

- `Co-Authored-By` を含めない
- 生成AIやエージェントの情報を含めない
- 署名や作者情報を追加しない
