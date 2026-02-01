---
name: create-pull-request
description: 現在のブランチの変更をステージング、コミットしてPull Requestを作成する。PR作成、プルリクエスト、変更をプッシュしてレビュー依頼する場合に使用。
allowed-tools: Bash
---

# PR作成スキル

現在のブランチの変更をコミットしてPull Requestを作成します。

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

   - 変更内容を分析して日本語でコミットメッセージを作成
   - 機能単位で簡潔に記述

   ```bash
   git commit -m "コミットメッセージ"
   ```

4. **リモートにプッシュ**

   ```bash
   git push -u origin <branch-name>
   ```

5. **Pull Request作成**

   ```bash
   gh pr create --title "PRタイトル" --body "$(cat <<'EOF'
   ## 概要
   変更内容の説明

   ## 変更点
   - 変更1
   - 変更2
   EOF
   )"
   ```

## 注意事項

- mainブランチで実行された場合は、先に新しいブランチを作成するか確認する
- コミットメッセージは日本語で記述
- PRのタイトルと本文は英語で記述
- 完了後、PRのURLを表示する
- PRの内容に誰が作成したか、どのコーディングエージェントが生成したかなどの情報は書かない（「🤖 Generated with Claude Code」などを含めない）
- PRの本文に「次のステップ」などの将来のタスクに関する記述は不要
