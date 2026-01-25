"""Database utilities for the tax return application using Supabase."""
import logging

import pandas as pd

from utils.supabase_client import get_current_user_id, get_supabase_client

logger = logging.getLogger(__name__)

# 許可されたrecord_type値
VALID_RECORD_TYPES = ('income', 'expense')


def _get_client():
    """Get the appropriate Supabase client."""
    return get_supabase_client()


# ===== Category Functions =====

# Default categories for new users
DEFAULT_INCOME_CATEGORIES = ['報酬', '給与', 'その他収入']
DEFAULT_EXPENSE_CATEGORIES = [
    '通信費', '交通費', '消耗品費', '接待交際費', '地代家賃',
    '水道光熱費', '広告宣伝費', '新聞図書費', '支払手数料', 'その他経費'
]


def _initialize_user_categories(user_id: str) -> bool:
    """Initialize default categories for a new user."""
    try:
        client = _get_client()

        categories = []
        for i, name in enumerate(DEFAULT_INCOME_CATEGORIES):
            categories.append({
                'user_id': user_id,
                'type': 'income',
                'name': name,
                'display_order': i
            })

        for i, name in enumerate(DEFAULT_EXPENSE_CATEGORIES):
            categories.append({
                'user_id': user_id,
                'type': 'expense',
                'name': name,
                'display_order': i
            })

        client.table('categories').insert(categories).execute()
        logger.info(f"Initialized categories for user: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error initializing categories: {e}")
        return False


def get_categories(record_type: str) -> list:
    """Get categories for a given record type for the current user."""
    if record_type not in VALID_RECORD_TYPES:
        raise ValueError(f"Invalid record_type: {record_type}")

    try:
        client = _get_client()
        user_id = get_current_user_id()

        query = client.table('categories').select('name').eq('type', record_type)

        if user_id:
            query = query.eq('user_id', user_id)

        response = query.order('display_order').execute()

        # If no categories found for this user, initialize defaults
        if user_id and not response.data:
            _initialize_user_categories(user_id)
            # Re-fetch after initialization
            response = client.table('categories') \
                .select('name') \
                .eq('type', record_type) \
                .eq('user_id', user_id) \
                .order('display_order') \
                .execute()

        if response.data:
            return [row['name'] for row in response.data]

        # Return defaults as fallback
        return DEFAULT_INCOME_CATEGORIES if record_type == 'income' else DEFAULT_EXPENSE_CATEGORIES

    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        return DEFAULT_INCOME_CATEGORIES if record_type == 'income' else DEFAULT_EXPENSE_CATEGORIES


def add_category(record_type: str, name: str) -> bool:
    """Add a new category for the current user if it doesn't exist."""
    if record_type not in VALID_RECORD_TYPES:
        raise ValueError(f"Invalid record_type: {record_type}")

    if not name or not name.strip():
        return False

    name = name.strip()

    try:
        client = _get_client()
        user_id = get_current_user_id()

        # Build query to check if exists
        query = client.table('categories').select('id').eq('type', record_type).eq('name', name)
        if user_id:
            query = query.eq('user_id', user_id)

        existing = query.execute()

        if existing.data:
            return False

        # Get max display_order for this user
        order_query = client.table('categories') \
            .select('display_order') \
            .eq('type', record_type)
        if user_id:
            order_query = order_query.eq('user_id', user_id)

        max_order_resp = order_query.order('display_order', desc=True).limit(1).execute()
        next_order = (max_order_resp.data[0]['display_order'] + 1) if max_order_resp.data else 0

        # Insert new category
        data = {
            'type': record_type,
            'name': name,
            'display_order': next_order
        }
        if user_id:
            data['user_id'] = user_id

        client.table('categories').insert(data).execute()

        logger.info(f"Category added: {record_type}/{name}")
        return True
    except Exception as e:
        logger.error(f"Error adding category: {e}")
        return False


def get_clients() -> list:
    """Get list of unique clients from records."""
    try:
        client = _get_client()
        response = client.table('records') \
            .select('client') \
            .neq('client', '') \
            .not_.is_('client', 'null') \
            .execute()

        # Get unique values
        clients = list({row['client'] for row in response.data if row['client']})
        return sorted(clients)
    except Exception as e:
        logger.error(f"Error getting clients: {e}")
        return []


def get_descriptions(limit: int = 50) -> list:
    """Get list of unique descriptions from records."""
    try:
        client = _get_client()
        response = client.table('records') \
            .select('description') \
            .neq('description', '') \
            .not_.is_('description', 'null') \
            .limit(500) \
            .execute()

        # Count occurrences and sort by frequency
        from collections import Counter
        descriptions = [row['description'] for row in response.data if row['description']]
        counter = Counter(descriptions)
        return [desc for desc, _ in counter.most_common(limit)]
    except Exception as e:
        logger.error(f"Error getting descriptions: {e}")
        return []


# ===== Record CRUD Functions =====

def save_record(record: dict) -> str | None:
    """Save a new record to the database."""
    try:
        client = _get_client()
        user_id = get_current_user_id()

        data = {
            'user_id': user_id,
            'date': record['date'],
            'type': record['type'],
            'category': record['category'],
            'client': record.get('client', ''),
            'description': record.get('description', ''),
            'currency': record.get('currency', 'JPY'),
            'amount_original': record['amount_original'],
            'ttm': record.get('ttm'),
            'amount_jpy': record['amount_jpy'],
            'withholding_tax': record.get('withholding_tax', False),
            'withholding_amount': record.get('withholding_amount', 0),
            'proration': record.get('proration', False),
            'proration_rate': record.get('proration_rate', 100),
            'amount_prorated': record['amount_prorated'],
            'attachment_path': record.get('attachment_path'),
            'fiscal_year': record['fiscal_year'],
        }

        response = client.table('records').insert(data).execute()

        if response.data:
            record_id = response.data[0]['id']
            logger.info(f"Record saved: {record_id}")
            return record_id
        return None
    except Exception as e:
        logger.error(f"Error saving record: {e}")
        raise


def update_record(record_id: str, record: dict) -> bool:
    """Update an existing record."""
    try:
        client = _get_client()

        data = {
            'date': record['date'],
            'type': record['type'],
            'category': record['category'],
            'client': record.get('client', ''),
            'description': record.get('description', ''),
            'currency': record.get('currency', 'JPY'),
            'amount_original': record['amount_original'],
            'ttm': record.get('ttm'),
            'amount_jpy': record['amount_jpy'],
            'withholding_tax': record.get('withholding_tax', False),
            'withholding_amount': record.get('withholding_amount', 0),
            'proration': record.get('proration', False),
            'proration_rate': record.get('proration_rate', 100),
            'amount_prorated': record['amount_prorated'],
            'attachment_path': record.get('attachment_path'),
            'fiscal_year': record['fiscal_year'],
        }

        response = client.table('records') \
            .update(data) \
            .eq('id', record_id) \
            .execute()

        success = len(response.data) > 0
        if success:
            logger.info(f"Record updated: {record_id}")
        return success
    except Exception as e:
        logger.error(f"Error updating record: {e}")
        return False


def delete_record(record_id: str) -> bool:
    """Delete a record."""
    try:
        client = _get_client()
        response = client.table('records') \
            .delete() \
            .eq('id', record_id) \
            .execute()

        success = len(response.data) > 0
        if success:
            logger.info(f"Record deleted: {record_id}")
        return success
    except Exception as e:
        logger.error(f"Error deleting record: {e}")
        return False


def get_record(record_id: str) -> dict | None:
    """Get a single record by ID."""
    try:
        client = _get_client()
        response = client.table('records') \
            .select('*') \
            .eq('id', record_id) \
            .single() \
            .execute()

        return response.data
    except Exception as e:
        logger.error(f"Error getting record: {e}")
        return None


def get_records(fiscal_year: int | None = None,
                record_type: str | None = None,
                category: str | None = None,
                start_date: str | None = None,
                end_date: str | None = None) -> pd.DataFrame:
    """Get records with optional filters.

    Note: Row Level Security (RLS) automatically filters by user_id.
    """
    if record_type and record_type not in VALID_RECORD_TYPES:
        raise ValueError(f"Invalid record_type: {record_type}")

    try:
        client = _get_client()
        query = client.table('records').select('*')

        if fiscal_year:
            query = query.eq('fiscal_year', fiscal_year)

        if record_type:
            query = query.eq('type', record_type)

        if category:
            query = query.eq('category', category)

        if start_date:
            query = query.gte('date', start_date)

        if end_date:
            query = query.lte('date', end_date)

        query = query.order('date', desc=True).order('created_at', desc=True)

        response = query.execute()

        if response.data:
            return pd.DataFrame(response.data)
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error getting records: {e}")
        return pd.DataFrame()


# ===== Summary Functions =====

def get_summary(fiscal_year: int) -> dict:
    """Get summary statistics for a fiscal year."""
    try:
        client = _get_client()

        # Get all records for the year
        response = client.table('records') \
            .select('type, amount_jpy, amount_prorated, withholding_amount') \
            .eq('fiscal_year', fiscal_year) \
            .execute()

        total_income = 0
        total_expense = 0
        total_withholding = 0

        for row in response.data:
            if row['type'] == 'income':
                total_income += row['amount_jpy'] or 0
                total_withholding += row['withholding_amount'] or 0
            else:
                total_expense += row['amount_prorated'] or 0

        return {
            'total_income': total_income,
            'total_expense': total_expense,
            'net_income': total_income - total_expense,
            'total_withholding': total_withholding
        }
    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        return {
            'total_income': 0,
            'total_expense': 0,
            'net_income': 0,
            'total_withholding': 0
        }


def get_category_summary(fiscal_year: int, record_type: str) -> pd.DataFrame:
    """Get summary by category for a fiscal year."""
    if record_type not in VALID_RECORD_TYPES:
        raise ValueError(f"Invalid record_type: {record_type}")

    try:
        client = _get_client()

        response = client.table('records') \
            .select('category, amount_jpy, amount_prorated') \
            .eq('fiscal_year', fiscal_year) \
            .eq('type', record_type) \
            .execute()

        if not response.data:
            return pd.DataFrame()

        df = pd.DataFrame(response.data)

        # Use appropriate amount column
        amount_col = 'amount_prorated' if record_type == 'expense' else 'amount_jpy'

        summary = df.groupby('category').agg(
            count=('category', 'size'),
            total=(amount_col, 'sum')
        ).reset_index()

        return summary.sort_values('total', ascending=False)
    except Exception as e:
        logger.error(f"Error getting category summary: {e}")
        return pd.DataFrame()


def get_client_summary(fiscal_year: int) -> pd.DataFrame:
    """Get summary by client for income records."""
    try:
        client = _get_client()

        response = client.table('records') \
            .select('client, amount_jpy, withholding_amount') \
            .eq('fiscal_year', fiscal_year) \
            .eq('type', 'income') \
            .neq('client', '') \
            .execute()

        if not response.data:
            return pd.DataFrame()

        df = pd.DataFrame(response.data)

        summary = df.groupby('client').agg(
            count=('client', 'size'),
            total_income=('amount_jpy', 'sum'),
            total_withholding=('withholding_amount', 'sum')
        ).reset_index()

        return summary.sort_values('total_income', ascending=False)
    except Exception as e:
        logger.error(f"Error getting client summary: {e}")
        return pd.DataFrame()


def get_monthly_summary(fiscal_year: int) -> pd.DataFrame:
    """Get monthly summary for a fiscal year."""
    try:
        client = _get_client()

        response = client.table('records') \
            .select('date, type, amount_jpy, amount_prorated') \
            .eq('fiscal_year', fiscal_year) \
            .execute()

        if not response.data:
            return pd.DataFrame()

        df = pd.DataFrame(response.data)
        df['month'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m')

        # Pivot to get income and expense by month
        income_df = df[df['type'] == 'income'].groupby('month')['amount_jpy'].sum()
        expense_df = df[df['type'] == 'expense'].groupby('month')['amount_prorated'].sum()

        summary = pd.DataFrame({
            'month': sorted(df['month'].unique()),
        })
        summary['income'] = summary['month'].map(income_df).fillna(0)
        summary['expense'] = summary['month'].map(expense_df).fillna(0)

        return summary
    except Exception as e:
        logger.error(f"Error getting monthly summary: {e}")
        return pd.DataFrame()


# ===== Settings Functions =====

def get_setting(key: str, default: str = '') -> str:
    """Get a setting value for the current user."""
    try:
        client = _get_client()
        user_id = get_current_user_id()

        query = client.table('settings').select('value').eq('key', key)

        # Filter by user_id if authenticated
        if user_id:
            query = query.eq('user_id', user_id)

        response = query.single().execute()

        return response.data['value'] if response.data else default
    except Exception:
        return default


def save_setting(key: str, value: str):
    """Save a setting value for the current user."""
    try:
        client = _get_client()
        user_id = get_current_user_id()

        data = {
            'key': key,
            'value': value
        }

        if user_id:
            data['user_id'] = user_id

            # Upsert with user_id + key as unique constraint
            client.table('settings').upsert(
                data,
                on_conflict='user_id,key'
            ).execute()
        else:
            # For unauthenticated users, just upsert by key
            client.table('settings').upsert(data).execute()

    except Exception as e:
        logger.error(f"Error saving setting: {e}")


# ===== Export Functions =====

def export_raw_records_to_csv(fiscal_year: int) -> str:
    """Export all record fields to CSV format (生データ出力)."""
    import io

    df = get_records(fiscal_year=fiscal_year)

    if df.empty:
        return ''

    # Sort by date
    df = df.sort_values('date')

    # Rename columns to Japanese
    column_mapping = {
        'id': 'ID',
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
        'proration': '按分対象',
        'proration_rate': '按分率(%)',
        'amount_prorated': '按分後金額',
        'attachment_path': '添付ファイル',
        'fiscal_year': '年度',
        'created_at': '作成日時',
    }

    # Only rename columns that exist
    df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

    # Map values to Japanese
    if '種別' in df.columns:
        df['種別'] = df['種別'].map({'income': '収入', 'expense': '経費'})
    if '源泉徴収有無' in df.columns:
        df['源泉徴収有無'] = df['源泉徴収有無'].apply(lambda x: 'あり' if x else '')
    if '按分対象' in df.columns:
        df['按分対象'] = df['按分対象'].apply(lambda x: 'あり' if x else '')

    # Select columns in order (only those that exist)
    export_cols = ['ID', '日付', '種別', '勘定科目', '取引先', '摘要', '通貨',
                   '金額(原通貨)', 'TTM', '金額(円)', '源泉徴収有無', '源泉徴収税額',
                   '按分対象', '按分率(%)', '按分後金額', '添付ファイル', '年度', '作成日時']
    export_cols = [col for col in export_cols if col in df.columns]

    output = io.StringIO()
    output.write(df[export_cols].to_csv(index=False))

    return output.getvalue()


def export_to_csv(fiscal_year: int) -> str:
    """Export records to CSV format for tax return (確定申告用)."""
    import io

    df = get_records(fiscal_year=fiscal_year)

    if df.empty:
        return ''

    output = io.StringIO()

    # ===== 1. サマリー =====
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

    # ===== 2. 経費内訳 =====
    expense_df = get_category_summary(fiscal_year, 'expense')
    output.write("# ===== 経費内訳（勘定科目別）=====\n")
    output.write("勘定科目,件数,金額（按分後）\n")
    if not expense_df.empty:
        for _, row in expense_df.iterrows():
            output.write(f"{row['category']},{row['count']},{int(row['total'])}\n")
    output.write("#\n")

    # ===== 3. 取引先別収入 =====
    client_df = get_client_summary(fiscal_year)
    output.write("# ===== 取引先別収入（支払調書照合用）=====\n")
    output.write("取引先,件数,収入金額,源泉徴収税額\n")
    if not client_df.empty:
        for _, row in client_df.iterrows():
            output.write(f"{row['client']},{row['count']},{int(row['total_income'])},{int(row['total_withholding'])}\n")
    output.write("#\n")

    # ===== 4. 収入内訳 =====
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
    df_export['源泉徴収有無'] = df_export['源泉徴収有無'].apply(lambda x: 'あり' if x else '')

    export_cols = ['日付', '種別', '勘定科目', '取引先', '摘要', '通貨',
                   '金額(原通貨)', 'TTM', '金額(円)', '源泉徴収有無', '源泉徴収税額',
                   '按分率(%)', '按分後金額']
    export_cols = [col for col in export_cols if col in df_export.columns]

    df_export = df_export.sort_values('日付')
    output.write(df_export[export_cols].to_csv(index=False))

    return output.getvalue()


def get_attachments_with_metadata(fiscal_year: int) -> list:
    """Get all attachments with metadata for a fiscal year.

    Args:
        fiscal_year: Fiscal year to get attachments for

    Returns:
        List of dicts with attachment_path, date, type, category, client, description
    """
    try:
        client = _get_client()

        response = client.table('records') \
            .select('attachment_path, date, type, category, client, description') \
            .eq('fiscal_year', fiscal_year) \
            .not_.is_('attachment_path', 'null') \
            .neq('attachment_path', '') \
            .order('date') \
            .execute()

        if response.data:
            return [row for row in response.data if row.get('attachment_path')]
        return []
    except Exception as e:
        logger.error(f"Error getting attachments with metadata: {e}")
        return []
