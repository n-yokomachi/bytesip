---
name: create-feature-branch
description: 新規機能開発用のfeatureブランチを作成する。新機能実装、feature作成、ブランチ切る場合に使用。
allowed-tools: Bash
---

# Featureブランチ作成スキル

新規機能開発用のfeatureブランチを作成します。

## 実行手順

1. **現在の状態確認**

   ```bash
   git status
   git branch
   ```

2. **mainブランチを最新化**

   ```bash
   git checkout main
   git pull origin main
   ```

3. **featureブランチ作成**

   - ブランチ名は `feature/機能名` の形式
   - 機能名は英語でケバブケース（例: `feature/add-lexer`）

   ```bash
   git checkout -b feature/<機能名>
   ```

4. **確認**
   ```bash
   git branch
   ```

## ブランチ命名規則

| プレフィックス | 用途             | 例                     |
| -------------- | ---------------- | ---------------------- |
| `feature/`     | 新機能           | `feature/add-parser`   |
| `fix/`         | バグ修正         | `fix/lexer-error`      |
| `refactor/`    | リファクタリング | `refactor/token-types` |

## 注意事項

- 未コミットの変更がある場合は、先にコミットまたはスタッシュするか確認する
- ブランチ名はユーザーに確認してから作成する
- コミットの内容に誰が作成したか、どのコーディングエージェントが生成したかなどの情報は書かない
