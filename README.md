# ABC Model Core API

FastAPI ベースの ABC モデルコア API サーバーです。

## 概要

- **バージョン**: 3.0.0
- **フレームワーク**: FastAPI
- **Python**: 3.11+
- **API キー認証**: 対応

## 機能

- ABC モデルのコア処理API
- API キーベースの認証
- Sentry によるエラートラッキング
- Docker対応

## セットアップ

### 前提条件

- Python 3.11 以上
- pip

### インストール

```bash
pip install -r requirements.txt
```

## 使用方法

### ローカル実行

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

API ドキュメント: http://localhost:8000/docs

### 環境変数

| 環境変数 | 説明 | 必須 |
|---------|------|------|
| API_KEY | APIアクセスに必要なキー | オプション |

### リクエスト例

```bash
curl -X GET http://localhost:8000/healthz \
  -H "x-api-key: your-api-key"
```

## Docker での実行

```bash
docker build -t abcmodel-api .
docker run -p 8000:8000 -e API_KEY=your-key abcmodel-api
```

## プロジェクト構成

```
abcmodel-api/
├── api/                 # FastAPI アプリケーション
│   ├── main.py         # メインのAPIサーバー
│   └── __init__.py
├── abcmodel_core/      # コアモジュール
│   ├── model.py        # ABCモデルの実装
│   ├── schemas.py      # Pydantic スキーマ
│   ├── config.py       # 設定
│   ├── enums.py        # 列挙型定義
│   ├── utils.py        # ユーティリティ関数
│   └── __init__.py
├── requirements.txt    # Python依存関係
├── Dockerfile         # Docker設定
└── README.md
```

## APIエンドポイント

### ヘルスチェック

```
GET /healthz
```

レスポンス:
```json
{"status": "ok"}
```

## トラッキング

エラーは Sentry で自動的にトラッキングされます。

## ライセンス

MITライセンス
