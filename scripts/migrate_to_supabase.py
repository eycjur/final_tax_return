#!/usr/bin/env python3
"""
SQLiteデータをSupabaseに移行するスクリプト

使用方法:
1. .envにSUPABASE_SERVICE_ROLE_KEYを追加
2. python scripts/migrate_to_supabase.py

注意: サービスロールキーはRLSをバイパスするため、管理者権限が必要です。
"""
import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# 設定
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
SQLITE_DB_PATH = Path(__file__).parent.parent / 'data' / 'tax_records.db'
ATTACHMENTS_DIR = Path(__file__).parent.parent / 'attachments'

# 移行対象のユーザーID
TARGET_USER_ID = '9f3c11bb-0cec-4d3c-bdf0-ab5af86d15e2'


def check_config():
    """設定を確認"""
    if not SUPABASE_URL:
        print("ERROR: SUPABASE_URL が設定されていません")
        return False
    if not SUPABASE_SERVICE_ROLE_KEY:
        print("ERROR: SUPABASE_SERVICE_ROLE_KEY が設定されていません")
        print("Supabase Dashboard > Settings > API > service_role key を .env に追加してください")
        return False
    if not SQLITE_DB_PATH.exists():
        print(f"ERROR: SQLiteデータベースが見つかりません: {SQLITE_DB_PATH}")
        return False
    return True


def get_sqlite_connection():
    """SQLite接続を取得"""
    return sqlite3.connect(SQLITE_DB_PATH)


def get_supabase_client():
    """Supabaseクライアントを取得（サービスロールキー使用）"""
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def migrate_categories(sqlite_conn, supabase):
    """カテゴリを移行"""
    print("\n=== カテゴリの移行 ===")

    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT type, name, display_order FROM categories")
    rows = cursor.fetchall()

    categories_data = []
    for row in rows:
        categories_data.append({
            'user_id': TARGET_USER_ID,
            'type': row[0],
            'name': row[1],
            'display_order': row[2]
        })

    if not categories_data:
        print("移行するカテゴリがありません")
        return 0

    # 既存のカテゴリを削除
    print(f"既存のカテゴリを削除中...")
    supabase.table('categories').delete().eq('user_id', TARGET_USER_ID).execute()

    # 新しいカテゴリを挿入
    print(f"{len(categories_data)}件のカテゴリを挿入中...")
    response = supabase.table('categories').insert(categories_data).execute()

    print(f"✓ {len(response.data)}件のカテゴリを移行しました")
    return len(response.data)


def migrate_settings(sqlite_conn, supabase):
    """設定を移行"""
    print("\n=== 設定の移行 ===")

    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    rows = cursor.fetchall()

    # gemini_api_keyはスキップ（環境変数で管理）
    settings_data = []
    for row in rows:
        if row[0] == 'gemini_api_key':
            continue
        settings_data.append({
            'user_id': TARGET_USER_ID,
            'key': row[0],
            'value': row[1]
        })

    if not settings_data:
        print("移行する設定がありません")
        return 0

    # 既存の設定を削除
    print(f"既存の設定を削除中...")
    supabase.table('settings').delete().eq('user_id', TARGET_USER_ID).execute()

    # 新しい設定を挿入
    print(f"{len(settings_data)}件の設定を挿入中...")
    response = supabase.table('settings').insert(settings_data).execute()

    print(f"✓ {len(response.data)}件の設定を移行しました")
    return len(response.data)


def migrate_records(sqlite_conn, supabase):
    """レコードを移行"""
    print("\n=== レコードの移行 ===")

    cursor = sqlite_conn.cursor()
    cursor.execute("""
        SELECT
            date, type, category, client, description, currency,
            amount_original, ttm, amount_jpy, withholding_tax, withholding_amount,
            proration, proration_rate, amount_prorated, attachment_path, fiscal_year,
            created_at, updated_at
        FROM records
    """)
    rows = cursor.fetchall()

    records_data = []
    for row in rows:
        # attachment_pathの形式を変更: 2025/filename.pdf → user_id/2025/filename.pdf
        attachment_path = row[14]
        if attachment_path:
            # すでにuser_idが含まれている場合はそのまま、そうでなければuser_idを追加
            if not attachment_path.startswith(TARGET_USER_ID):
                attachment_path = f"{TARGET_USER_ID}/{attachment_path}"

        records_data.append({
            'user_id': TARGET_USER_ID,
            'date': row[0],
            'type': row[1],
            'category': row[2],
            'client': row[3] or '',
            'description': row[4] or '',
            'currency': row[5] or 'JPY',
            'amount_original': row[6],
            'ttm': row[7],
            'amount_jpy': row[8],
            'withholding_tax': bool(row[9]),
            'withholding_amount': row[10] or 0,
            'proration': bool(row[11]),
            'proration_rate': row[12] or 100,
            'amount_prorated': row[13],
            'attachment_path': attachment_path,
            'fiscal_year': row[15],
        })

    if not records_data:
        print("移行するレコードがありません")
        return 0

    # 既存のレコードを削除
    print(f"既存のレコードを削除中...")
    supabase.table('records').delete().eq('user_id', TARGET_USER_ID).execute()

    # 新しいレコードを挿入
    print(f"{len(records_data)}件のレコードを挿入中...")
    response = supabase.table('records').insert(records_data).execute()

    print(f"✓ {len(response.data)}件のレコードを移行しました")
    return len(response.data)


def migrate_attachments(supabase):
    """添付ファイルをSupabase Storageに移行"""
    print("\n=== 添付ファイルの移行 ===")

    if not ATTACHMENTS_DIR.exists():
        print("添付ファイルディレクトリが見つかりません")
        return 0

    uploaded_count = 0

    # 年度ごとのディレクトリを走査
    for year_dir in ATTACHMENTS_DIR.iterdir():
        if not year_dir.is_dir():
            continue

        year = year_dir.name
        print(f"\n{year}年度のファイルを処理中...")

        for file_path in year_dir.iterdir():
            if not file_path.is_file():
                continue

            # Supabase Storageのパス: user_id/year/filename
            storage_path = f"{TARGET_USER_ID}/{year}/{file_path.name}"

            try:
                # ファイルを読み込み
                with open(file_path, 'rb') as f:
                    file_data = f.read()

                # MIMEタイプを決定
                ext = file_path.suffix.lower()
                mime_types = {
                    '.pdf': 'application/pdf',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                }
                content_type = mime_types.get(ext, 'application/octet-stream')

                # アップロード（既存ファイルは上書き）
                supabase.storage.from_('attachments').upload(
                    storage_path,
                    file_data,
                    file_options={"content-type": content_type, "upsert": "true"}
                )

                print(f"  ✓ {file_path.name}")
                uploaded_count += 1

            except Exception as e:
                print(f"  ✗ {file_path.name}: {e}")

    print(f"\n✓ {uploaded_count}件のファイルをアップロードしました")
    return uploaded_count


def main():
    print("=" * 50)
    print("SQLite → Supabase データ移行スクリプト")
    print("=" * 50)
    print(f"対象ユーザーID: {TARGET_USER_ID}")
    print(f"SQLiteデータベース: {SQLITE_DB_PATH}")

    # 設定確認
    if not check_config():
        sys.exit(1)

    # 接続
    sqlite_conn = get_sqlite_connection()
    supabase = get_supabase_client()

    try:
        # カテゴリの移行
        migrate_categories(sqlite_conn, supabase)

        # 設定の移行
        migrate_settings(sqlite_conn, supabase)

        # レコードの移行
        migrate_records(sqlite_conn, supabase)

        # 添付ファイルの移行
        migrate_attachments(supabase)

        print("\n" + "=" * 50)
        print("✓ 移行が完了しました！")
        print("=" * 50)

    except Exception as e:
        print(f"\nERROR: 移行中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        sqlite_conn.close()


if __name__ == '__main__':
    main()
