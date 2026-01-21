# 確定申告収支記録アプリケーション

個人事業主・フリーランス向けの確定申告用収支記録Webアプリケーションです。
Supabaseを使用したマルチユーザー対応で、Google SSOによる認証機能を備えています。

## 機能

### 基本機能
- 収入・支出の記録管理
- 日本円(JPY)・米ドル(USD)対応
- TTM（電信仲値）による自動円換算
- 源泉徴収の管理（自動計算対応）
- 按分機能（家賃、通信費などの経費按分）

### ファイル管理
- PDF・画像ファイルのアップロード（Supabase Storage）
- スマホカメラでの領収書撮影
- 年度別の添付ファイル一括ダウンロード（ZIP形式）

### AI機能
- Gemini APIによる領収書・請求書の自動解析
- 日付・金額・取引先・カテゴリの自動抽出

### レポート機能
- 年間サマリー（収入・経費・所得・源泉徴収）
- カテゴリ別集計
- 取引先別集計（支払調書照合用）
- 月別推移グラフ
- CSVエクスポート（生データ・確定申告用サマリー）

### マルチユーザー対応
- Google SSOによる認証
- ユーザーごとのデータ分離（RLS）
- ユーザー別カテゴリ・設定管理

## セットアップ

### 1. Supabaseプロジェクトの作成

1. [Supabase](https://supabase.com/) でアカウント作成・新規プロジェクト作成
2. **Settings > API** から以下の情報を取得:
   - Project URL
   - anon public key

### 2. データベースのセットアップ

Supabase Dashboard の **SQL Editor** で以下を実行:

```bash
# マイグレーションファイルの内容を実行
supabase/migrations/001_initial_schema.sql
```

### 3. Google OAuth の設定

1. [Google Cloud Console](https://console.cloud.google.com/) でOAuthクライアントを作成
2. Supabase Dashboard > **Authentication > Providers > Google** を有効化
3. Client ID と Client Secret を設定

### 4. Storage バケットの作成

Supabase Dashboard > **Storage** で:
- Bucket name: `attachments`
- Public bucket: OFF (private)
- File size limit: 10MB
- Allowed MIME types: `image/jpeg, image/png, application/pdf, image/gif`

### 5. アプリケーションのインストール

```bash
# uvがインストールされていない場合
curl -LsSf https://astral.sh/uv/install.sh | sh

# プロジェクトディレクトリに移動
cd final_tax_return

# 依存パッケージをインストール
uv sync

# 環境変数ファイルを作成
cp .env.example .env
```

### 6. 環境変数の設定

`.env` ファイルを編集:

```bash
# Supabase設定（必須）
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_ANON_KEY=your-anon-key

# 認証設定
AUTH_ENABLED=true  # false: 認証なし（ローカル開発用）

# Gemini API設定（オプション - AI自動入力機能を使う場合）
GEMINI_API_KEY=your-gemini-api-key
```

## 使い方

### アプリケーションの起動

```bash
uv run python index.py
```

ブラウザで `http://localhost:8050` を開いてください。

### 基本的な使い方

1. **ログイン**: Googleアカウントでサインイン
2. **収支記録**: 「新規記録」ボタンで収支を入力
3. **AI自動入力**: 領収書をアップロードして「Geminiで自動入力」
4. **レポート**: 確定申告用のカテゴリ別・取引先別集計を確認
5. **設定**: 按分率のプリセットを設定

### 添付ファイルの管理

- 添付ファイルは Supabase Storage に保存（ユーザー別ディレクトリ）
- 「添付」ボタンで年度ごとの全ファイルをZIPダウンロード
- ZIP内は月別ディレクトリで整理（例: `2024-03/2024-03-15_経費_通信費_NTT.pdf`）

## ディレクトリ構造

```
final_tax_return/
├── app.py                  # Dashアプリケーション初期化
├── index.py                # メインエントリーポイント・ルーティング
├── pyproject.toml          # プロジェクト設定・依存パッケージ
├── .env.example            # 環境変数のサンプル
├── assets/
│   ├── style.css           # スタイルシート
│   └── supabase-auth.js    # Supabase認証クライアント
├── pages/
│   ├── __init__.py
│   ├── records.py          # 収支記録一覧・入力フォーム
│   ├── report.py           # レポート・集計画面
│   ├── settings.py         # 設定画面
│   └── login.py            # ログイン画面
├── components/
│   └── common.py           # 共通UIコンポーネント
├── utils/
│   ├── database.py         # Supabaseデータベース操作
│   ├── calculations.py     # 計算ロジック
│   ├── gemini.py           # Gemini API連携
│   ├── storage.py          # Supabase Storage操作
│   ├── supabase_client.py  # Supabaseクライアント設定
│   └── auth.py             # 認証ユーティリティ
└── supabase/
    └── migrations/
        └── 001_initial_schema.sql  # データベーススキーマ
```

## データベーススキーマ

| テーブル | 説明 | RLS |
|----------|------|:---:|
| `records` | 収支記録 | ✅ |
| `categories` | カテゴリマスタ（ユーザー別） | ✅ |
| `settings` | ユーザー設定 | ✅ |
| `storage.objects` | 添付ファイル | ✅ |

すべてのデータはRow Level Security (RLS) により、ユーザー自身のデータのみアクセス可能です。

## 確定申告での利用

### 収入の記録
- 請求書発行時または入金時に記録
- 源泉徴収がある場合はチェックを入れる（自動計算）
- USD収入の場合は入金日のTTMを記録

### 経費の記録
- 按分が必要な経費（家賃、通信費など）は按分率を設定
- 領収書をアップロードまたは撮影して添付
- Gemini AIで自動入力も可能

### レポート出力
- 確定申告時に「レポート」画面で集計を確認
- CSVダウンロードで確定申告書への転記に利用
- 添付ファイル一括ダウンロードで証跡を保管

## 開発

### ローカル開発（認証なし）

```bash
# .envファイルで認証を無効化
AUTH_ENABLED=false
```

### デバッグモード

```bash
uv run python index.py
# デフォルトでdebug=Trueで起動
```

## 注意事項

- このアプリケーションは記録・集計の補助ツールです
- 最終的な確定申告は税理士への相談を推奨します
- Supabase の無料枠には制限があります（詳細は[公式ドキュメント](https://supabase.com/pricing)参照）

## ライセンス

MIT License
