# TeamFlow（業務タスク管理API）

## 概要

チーム開発を想定したタスク管理ツールのバックエンドAPIです。
認証（JWT）、プロジェクト管理、タスク管理、ステータス更新を実装しています。

## 主要機能

- [ ] ユーザー登録 / ログイン（JWT） ※ログインは未完了（実装中）
- [x] プロジェクト作成 / 一覧 / 削除
- [x] タスク作成 / 一覧（statusフィルタ）/ ステータス更新（todo/doing/done）

## 技術スタック

- Python / FastAPI
- SQLAlchemy
- SQLite（開発用）
- JWT（python-jose）
- bcrypt

## 起動方法

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload