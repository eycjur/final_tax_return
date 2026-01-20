"""Database utilities for the tax return application."""
import sqlite3
import os
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Optional
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'tax_records.db')
logger = logging.getLogger(__name__)

# 許可されたrecord_type値
VALID_RECORD_TYPES = ('income', 'expense')


@contextmanager
def get_connection():
    """Get a database connection with context manager."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize the database with required tables."""
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                category TEXT NOT NULL,
                client TEXT,
                description TEXT,
                currency TEXT DEFAULT 'JPY' CHECK(currency IN ('JPY', 'USD')),
                amount_original REAL NOT NULL,
                ttm REAL,
                amount_jpy REAL NOT NULL,
                withholding_tax INTEGER DEFAULT 0,
                withholding_amount REAL DEFAULT 0,
                proration INTEGER DEFAULT 0,
                proration_rate REAL DEFAULT 100,
                amount_prorated REAL NOT NULL,
                attachment_path TEXT,
                fiscal_year INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                name TEXT NOT NULL,
                display_order INTEGER DEFAULT 0,
                UNIQUE(type, name)
            )
        ''')

        # インデックスの作成（検索パフォーマンス向上）
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_records_fiscal_year ON records(fiscal_year)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_records_type ON records(type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_records_date ON records(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_records_category ON records(category)')

        default_income_categories = ['報酬', '給与', 'その他収入']
        default_expense_categories = [
            '通信費', '交通費', '消耗品費', '接待交際費', '地代家賃',
            '水道光熱費', '広告宣伝費', '新聞図書費', '支払手数料', 'その他経費'
        ]

        for i, cat in enumerate(default_income_categories):
            cursor.execute('''
                INSERT OR IGNORE INTO categories (type, name, display_order)
                VALUES ('income', ?, ?)
            ''', (cat, i))

        for i, cat in enumerate(default_expense_categories):
            cursor.execute('''
                INSERT OR IGNORE INTO categories (type, name, display_order)
                VALUES ('expense', ?, ?)
            ''', (cat, i))

        conn.commit()


def get_categories(record_type: str) -> list:
    """Get categories for a given record type."""
    if record_type not in VALID_RECORD_TYPES:
        raise ValueError(f"Invalid record_type: {record_type}")

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT name FROM categories
            WHERE type = ?
            ORDER BY display_order
        ''', (record_type,))
        categories = [row['name'] for row in cursor.fetchall()]
    return categories


def add_category(record_type: str, name: str) -> bool:
    """Add a new category if it doesn't exist.

    Returns True if the category was added, False if it already existed.
    """
    if record_type not in VALID_RECORD_TYPES:
        raise ValueError(f"Invalid record_type: {record_type}")

    if not name or not name.strip():
        return False

    name = name.strip()

    with get_connection() as conn:
        cursor = conn.cursor()
        # 現在の最大display_orderを取得
        cursor.execute('''
            SELECT MAX(display_order) as max_order FROM categories WHERE type = ?
        ''', (record_type,))
        row = cursor.fetchone()
        next_order = (row['max_order'] or 0) + 1

        try:
            cursor.execute('''
                INSERT INTO categories (type, name, display_order)
                VALUES (?, ?, ?)
            ''', (record_type, name, next_order))
            conn.commit()
            logger.info(f"Category added: {record_type}/{name}")
            return True
        except sqlite3.IntegrityError:
            # 既に存在する場合
            return False


def get_clients() -> list:
    """Get list of unique clients from records."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT client FROM records
            WHERE client IS NOT NULL AND client != ''
            ORDER BY client
        ''')
        clients = [row['client'] for row in cursor.fetchall()]
    return clients


def get_descriptions(limit: int = 50) -> list:
    """Get list of unique descriptions from records, ordered by frequency.

    Args:
        limit: Maximum number of descriptions to return (default 50)

    Returns:
        List of unique description strings
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT description, COUNT(*) as cnt FROM records
            WHERE description IS NOT NULL AND description != ''
            GROUP BY description
            ORDER BY cnt DESC, description
            LIMIT ?
        ''', (limit,))
        descriptions = [row['description'] for row in cursor.fetchall()]
    return descriptions


def save_record(record: dict) -> int:
    """Save a new record to the database."""
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO records (
                date, type, category, client, description,
                currency, amount_original, ttm, amount_jpy,
                withholding_tax, withholding_amount,
                proration, proration_rate, amount_prorated,
                attachment_path, fiscal_year
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record['date'],
            record['type'],
            record['category'],
            record.get('client', ''),
            record.get('description', ''),
            record.get('currency', 'JPY'),
            record['amount_original'],
            record.get('ttm'),
            record['amount_jpy'],
            record.get('withholding_tax', 0),
            record.get('withholding_amount', 0),
            record.get('proration', 0),
            record.get('proration_rate', 100),
            record['amount_prorated'],
            record.get('attachment_path'),
            record['fiscal_year']
        ))

        record_id = cursor.lastrowid
        conn.commit()
        logger.info(f"Record saved: {record_id}")
    return record_id


def update_record(record_id: int, record: dict) -> bool:
    """Update an existing record."""
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE records SET
                date = ?, type = ?, category = ?, client = ?, description = ?,
                currency = ?, amount_original = ?, ttm = ?, amount_jpy = ?,
                withholding_tax = ?, withholding_amount = ?,
                proration = ?, proration_rate = ?, amount_prorated = ?,
                attachment_path = ?, fiscal_year = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            record['date'],
            record['type'],
            record['category'],
            record.get('client', ''),
            record.get('description', ''),
            record.get('currency', 'JPY'),
            record['amount_original'],
            record.get('ttm'),
            record['amount_jpy'],
            record.get('withholding_tax', 0),
            record.get('withholding_amount', 0),
            record.get('proration', 0),
            record.get('proration_rate', 100),
            record['amount_prorated'],
            record.get('attachment_path'),
            record['fiscal_year'],
            record_id
        ))

        success = cursor.rowcount > 0
        conn.commit()
        if success:
            logger.info(f"Record updated: {record_id}")
    return success


def delete_record(record_id: int) -> bool:
    """Delete a record."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM records WHERE id = ?', (record_id,))
        success = cursor.rowcount > 0
        conn.commit()
        if success:
            logger.info(f"Record deleted: {record_id}")
    return success


def get_record(record_id: int) -> Optional[dict]:
    """Get a single record by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM records WHERE id = ?', (record_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
    return None


def get_records(fiscal_year: Optional[int] = None,
                record_type: Optional[str] = None,
                category: Optional[str] = None,
                start_date: Optional[str] = None,
                end_date: Optional[str] = None) -> pd.DataFrame:
    """Get records with optional filters."""
    # record_typeの検証
    if record_type and record_type not in VALID_RECORD_TYPES:
        raise ValueError(f"Invalid record_type: {record_type}")

    query = 'SELECT * FROM records WHERE 1=1'
    params = []

    if fiscal_year:
        query += ' AND fiscal_year = ?'
        params.append(fiscal_year)

    if record_type:
        query += ' AND type = ?'
        params.append(record_type)

    if category:
        query += ' AND category = ?'
        params.append(category)

    if start_date:
        query += ' AND date >= ?'
        params.append(start_date)

    if end_date:
        query += ' AND date <= ?'
        params.append(end_date)

    query += ' ORDER BY date DESC, id DESC'

    with get_connection() as conn:
        df = pd.read_sql_query(query, conn, params=params)
    return df


def get_summary(fiscal_year: int) -> dict:
    """Get summary statistics for a fiscal year."""
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                SUM(CASE WHEN type = 'income' THEN amount_jpy ELSE 0 END) as total_income,
                SUM(CASE WHEN type = 'expense' THEN amount_prorated ELSE 0 END) as total_expense,
                SUM(CASE WHEN type = 'income' THEN withholding_amount ELSE 0 END) as total_withholding
            FROM records
            WHERE fiscal_year = ?
        ''', (fiscal_year,))

        row = cursor.fetchone()

    total_income = row['total_income'] or 0
    total_expense = row['total_expense'] or 0
    total_withholding = row['total_withholding'] or 0

    return {
        'total_income': total_income,
        'total_expense': total_expense,
        'net_income': total_income - total_expense,
        'total_withholding': total_withholding
    }


def get_category_summary(fiscal_year: int, record_type: str) -> pd.DataFrame:
    """Get summary by category for a fiscal year."""
    # SQLインジェクション対策: record_typeを検証
    if record_type not in VALID_RECORD_TYPES:
        raise ValueError(f"Invalid record_type: {record_type}")

    # 検証済みの値のみを使用するため安全
    if record_type == 'expense':
        amount_col = 'amount_prorated'
    else:
        amount_col = 'amount_jpy'

    query = f'''
        SELECT
            category,
            COUNT(*) as count,
            SUM({amount_col}) as total
        FROM records
        WHERE fiscal_year = ? AND type = ?
        GROUP BY category
        ORDER BY total DESC
    '''

    with get_connection() as conn:
        df = pd.read_sql_query(query, conn, params=(fiscal_year, record_type))
    return df


def get_client_summary(fiscal_year: int) -> pd.DataFrame:
    """Get summary by client for income records."""
    query = '''
        SELECT
            client,
            COUNT(*) as count,
            SUM(amount_jpy) as total_income,
            SUM(withholding_amount) as total_withholding
        FROM records
        WHERE fiscal_year = ? AND type = 'income' AND client != ''
        GROUP BY client
        ORDER BY total_income DESC
    '''

    with get_connection() as conn:
        df = pd.read_sql_query(query, conn, params=(fiscal_year,))
    return df


def get_monthly_summary(fiscal_year: int) -> pd.DataFrame:
    """Get monthly summary for a fiscal year."""
    query = '''
        SELECT
            strftime('%Y-%m', date) as month,
            SUM(CASE WHEN type = 'income' THEN amount_jpy ELSE 0 END) as income,
            SUM(CASE WHEN type = 'expense' THEN amount_prorated ELSE 0 END) as expense
        FROM records
        WHERE fiscal_year = ?
        GROUP BY month
        ORDER BY month
    '''

    with get_connection() as conn:
        df = pd.read_sql_query(query, conn, params=(fiscal_year,))
    return df


def get_setting(key: str, default: str = '') -> str:
    """Get a setting value."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        row = cursor.fetchone()
    return row['value'] if row else default


def save_setting(key: str, value: str):
    """Save a setting value."""
    # セキュリティ警告: APIキーはDBに保存される
    if key == 'gemini_api_key' and value:
        logger.warning("APIキーがデータベースに保存されます。本番環境では環境変数の使用を推奨します。")

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value)
            VALUES (?, ?)
        ''', (key, value))
        conn.commit()


def export_to_csv(fiscal_year: int) -> str:
    """Export records to CSV format for tax return (確定申告用).

    CSV structure:
    1. Summary section (サマリー)
    2. Expense breakdown by category (経費内訳)
    3. Income by client with withholding tax (取引先別収入・源泉徴収)
    4. Detailed records (明細データ)
    """
    import io

    df = get_records(fiscal_year=fiscal_year)

    if df.empty:
        return ''

    output = io.StringIO()

    # ===== 1. サマリー（確定申告書に転記する数値）=====
    summary = get_summary(fiscal_year)
    output.write(f"# {fiscal_year}年分 確定申告用データ\n")
    output.write("#\n")
    output.write("# ===== サマリー（確定申告書転記用）=====\n")
    output.write("項目,金額\n")
    output.write(f"収入金額合計,{int(summary['total_income'])}\n")
    output.write(f"必要経費合計,{int(summary['total_expense'])}\n")
    output.write(f"所得金額（収入－経費）,{int(summary['net_income'])}\n")
    output.write(f"源泉徴収税額合計,{int(summary['total_withholding'])}\n")
    output.write("#\n")

    # ===== 2. 経費内訳（青色申告決算書の経費欄用）=====
    expense_df = get_category_summary(fiscal_year, 'expense')
    output.write("# ===== 経費内訳（勘定科目別）=====\n")
    output.write("勘定科目,件数,金額（按分後）\n")
    if not expense_df.empty:
        for _, row in expense_df.iterrows():
            output.write(f"{row['category']},{row['count']},{int(row['total'])}\n")
    output.write("#\n")

    # ===== 3. 取引先別収入（支払調書との照合用）=====
    client_df = get_client_summary(fiscal_year)
    output.write("# ===== 取引先別収入（支払調書照合用）=====\n")
    output.write("取引先,件数,収入金額,源泉徴収税額\n")
    if not client_df.empty:
        for _, row in client_df.iterrows():
            output.write(f"{row['client']},{row['count']},{int(row['total_income'])},{int(row['total_withholding'])}\n")
    output.write("#\n")

    # ===== 4. 収入内訳（カテゴリ別）=====
    income_df = get_category_summary(fiscal_year, 'income')
    output.write("# ===== 収入内訳（カテゴリ別）=====\n")
    output.write("カテゴリ,件数,金額\n")
    if not income_df.empty:
        for _, row in income_df.iterrows():
            output.write(f"{row['category']},{row['count']},{int(row['total'])}\n")
    output.write("#\n")

    # ===== 5. 明細データ =====
    output.write("# ===== 明細データ =====\n")

    df_export = df.copy()
    df_export = df_export.rename(columns={
        'date': '日付',
        'type': '種別',
        'category': '勘定科目',
        'client': '取引先',
        'description': '摘要',
        'currency': '通貨',
        'amount_original': '金額(原通貨)',
        'ttm': 'TTM',
        'amount_jpy': '金額(円)',
        'withholding_tax': '源泉徴収有無',
        'withholding_amount': '源泉徴収税額',
        'proration_rate': '按分率(%)',
        'amount_prorated': '按分後金額'
    })

    df_export['種別'] = df_export['種別'].map({'income': '収入', 'expense': '経費'})
    df_export['源泉徴収有無'] = df_export['源泉徴収有無'].map({0: '', 1: 'あり'})

    export_cols = ['日付', '種別', '勘定科目', '取引先', '摘要', '通貨',
                   '金額(原通貨)', 'TTM', '金額(円)', '源泉徴収有無', '源泉徴収税額',
                   '按分率(%)', '按分後金額']

    # Sort by date
    df_export = df_export.sort_values('日付')

    output.write(df_export[export_cols].to_csv(index=False))

    return output.getvalue()


init_db()
