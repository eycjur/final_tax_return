"""Callbacks for the records page."""
import base64
import os
from datetime import date, datetime

from dash import callback_context, html, no_update
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from app import app
from components.common import create_summary_cards
from utils import calculations as calc
from utils import database as db
from utils import gemini
from utils import storage
from utils import validation as valid
from utils.supabase_client import ensure_session_from_auth_data

from .form import create_record_form

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ATTACHMENTS_DIR = os.path.join(BASE_DIR, 'attachments')


# =============================================================================
# Records List Callbacks
# =============================================================================

@app.callback(
    [Output('records-summary', 'children'),
     Output('records-table', 'data'),
     Output('records-empty-state', 'style'),
     Output('records-table', 'style_table')],
    [Input('records-year', 'value'),
     Input('records-type-filter', 'value'),
     Input('store-records-data', 'data'),
     Input('store-auth-session', 'data')]
)
def update_records_list(year, type_filter, _, auth_session):
    """Update records list and summary cards."""
    if not year:
        raise PreventUpdate

    ensure_session_from_auth_data(auth_session)
    year = int(year)

    # Get summary for the year (always show full summary regardless of filter)
    summary = db.get_summary(year)
    summary_cards = create_summary_cards(summary)

    # Get filtered records for the table
    record_type = None if type_filter == 'all' else type_filter
    df = db.get_records(fiscal_year=year, record_type=record_type)

    if df.empty:
        # Show empty state, hide table
        return summary_cards, [], {'display': 'block'}, {'display': 'none'}

    # Prepare data for DataTable
    df = df.copy()
    df['type_display'] = df['type'].map({'income': '収入', 'expense': '支出'})
    df['amount_display'] = df['amount_jpy'].apply(lambda x: calc.format_currency(x))
    df['prorated_display'] = df['amount_prorated'].apply(lambda x: calc.format_currency(x))

    # Hide empty state, show table
    return summary_cards, df.to_dict('records'), {'display': 'none'}, {'overflowX': 'auto'}


# =============================================================================
# Category Callbacks
# =============================================================================

@app.callback(
    Output('category-datalist', 'children'),
    [Input('input-type', 'value'),
     Input('store-auth-session', 'data')]
)
def update_category_options(record_type, auth_session):
    """Update category datalist options based on record type."""
    if not record_type:
        return []

    ensure_session_from_auth_data(auth_session)
    categories = db.get_categories(record_type)
    return [html.Option(value=c) for c in categories]


# =============================================================================
# Currency & Calculation Callbacks
# =============================================================================

@app.callback(
    [Output('input-ttm', 'disabled'),
     Output('ttm-lookup-link', 'children')],
    [Input('input-currency', 'value'),
     Input('input-date', 'value')]
)
def toggle_ttm_input(currency, date_val):
    """Enable/disable TTM input and show lookup link based on currency."""
    if currency != 'USD':
        return True, ''

    # Build TTM lookup URL with date parameters
    if date_val:
        try:
            parts = date_val.split('-')
            if len(parts) == 3:
                year, month, day = parts
                # Remove leading zeros for URL params
                month = str(int(month))
                day = str(int(day))
                url = f"https://www.murc-kawasesouba.jp/fx/past_3month_result.php?y={year}&m={month}&d={day}&c="
            else:
                url = "https://www.murc-kawasesouba.jp/fx/past_3month.php?caution=1"
        except (ValueError, IndexError):
            url = "https://www.murc-kawasesouba.jp/fx/past_3month.php?caution=1"
    else:
        url = "https://www.murc-kawasesouba.jp/fx/past_3month.php?caution=1"

    link = html.A(
        [html.I(className="fas fa-external-link-alt me-1"), "TTMを調べる"],
        href=url,
        target="_blank",
        className="small"
    )
    return False, link


@app.callback(
    [Output('display-jpy', 'value'),
     Output('display-prorated', 'value')],
    [Input('input-amount', 'value'),
     Input('input-currency', 'value'),
     Input('input-ttm', 'value'),
     Input('input-proration', 'value'),
     Input('input-proration-rate', 'value')]
)
def calculate_amounts(amount, currency, ttm, proration, proration_rate):
    """Calculate JPY and prorated amounts."""
    if not amount:
        return '', ''
    try:
        amount = float(amount)
        if currency == 'USD' and ttm:
            jpy_amount = calc.calculate_jpy_amount(amount, currency, float(ttm))
        elif currency == 'JPY':
            jpy_amount = amount
        else:
            return '', ''
        if proration and proration_rate:
            prorated = calc.calculate_prorated_amount(jpy_amount, float(proration_rate))
        else:
            prorated = jpy_amount
        return calc.format_currency(jpy_amount), calc.format_currency(prorated)
    except (ValueError, TypeError):
        return '', ''


@app.callback(
    [Output('input-withholding-amount', 'disabled'),
     Output('input-withholding-amount', 'value')],
    [Input('input-withholding', 'value'),
     Input('input-amount', 'value'),
     Input('input-currency', 'value'),
     Input('input-ttm', 'value')]
)
def toggle_withholding(withholding, amount, currency, ttm):
    """Toggle and calculate withholding tax."""
    if not withholding:
        return True, ''
    if not amount:
        return False, ''
    try:
        amount = float(amount)
        if currency == 'USD' and ttm:
            jpy_amount = calc.calculate_jpy_amount(amount, currency, float(ttm))
        elif currency == 'JPY':
            jpy_amount = amount
        else:
            return False, ''
        withholding_amount = calc.calculate_withholding_tax(jpy_amount)
        return False, int(withholding_amount)
    except (ValueError, TypeError):
        return False, ''


@app.callback(
    [Output('input-proration-rate', 'disabled'),
     Output('input-proration-rate', 'value')],
    [Input('input-proration', 'value'),
     Input('input-category', 'value')]
)
def toggle_proration(proration, category):
    """Toggle proration rate input."""
    if not proration:
        return True, 100
    preset_rates = {
        '地代家賃': db.get_setting('preset_rent_rate', '50'),
        '通信費': db.get_setting('preset_comm_rate', '50'),
        '水道光熱費': db.get_setting('preset_utility_rate', '30'),
    }
    rate = preset_rates.get(category, '100')
    return False, int(rate)


# =============================================================================
# Modal Callbacks
# =============================================================================

@app.callback(
    [Output('form-modal', 'is_open'),
     Output('modal-title', 'children'),
     Output('modal-body', 'children'),
     Output('store-edit-id', 'data')],
    [Input('btn-new-record', 'n_clicks'),
     Input('btn-edit-selected', 'n_clicks'),
     Input('btn-duplicate-selected', 'n_clicks'),
     Input('btn-cancel', 'n_clicks')],
    [State('records-table', 'selected_rows'),
     State('records-table', 'data'),
     State('form-modal', 'is_open')],
    prevent_initial_call=True
)
def toggle_form_modal(new_click, edit_click, dup_click, cancel_click,
                      selected_rows, table_data, _is_open):
    """Toggle record form modal (open/cancel only, save is handled separately)."""
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate

    triggered = ctx.triggered[0]
    trigger_id = triggered['prop_id'].split('.')[0]
    trigger_value = triggered['value']

    # Ignore initial render (when n_clicks is None or 0)
    if not trigger_value:
        raise PreventUpdate

    if trigger_id == 'btn-cancel':
        return False, '', '', None
    if trigger_id == 'btn-new-record':
        return True, '新規記録', create_record_form(), None
    if trigger_id == 'btn-edit-selected' and selected_rows and table_data:
        record_data = table_data[selected_rows[0]]
        record = db.get_record(record_data.get('id'))
        if record:
            return True, '記録を編集', create_record_form(record), record.get('id')
    if trigger_id == 'btn-duplicate-selected' and selected_rows and table_data:
        record_data = table_data[selected_rows[0]]
        record = db.get_record(record_data.get('id'))
        if record:
            record['id'] = None
            record['date'] = date.today().isoformat()
            return True, '記録を複製', create_record_form(record), None
    raise PreventUpdate


# =============================================================================
# CRUD Callbacks
# =============================================================================

@app.callback(
    [Output('store-records-data', 'data'),
     Output('toast-notification', 'children'),
     Output('toast-notification', 'is_open'),
     Output('toast-notification', 'header'),
     Output('form-modal', 'is_open', allow_duplicate=True),
     Output('store-edit-id', 'data', allow_duplicate=True)],
    Input('btn-save', 'n_clicks'),
    [State('input-date', 'value'),
     State('input-type', 'value'),
     State('input-category', 'value'),
     State('input-client', 'value'),
     State('input-description', 'value'),
     State('input-currency', 'value'),
     State('input-amount', 'value'),
     State('input-ttm', 'value'),
     State('input-withholding', 'value'),
     State('input-withholding-amount', 'value'),
     State('input-proration', 'value'),
     State('input-proration-rate', 'value'),
     State('store-edit-id', 'data'),
     State('store-attachment-data', 'data'),
     State('store-attachment-name', 'data'),
     State('store-auth-session', 'data')],
    prevent_initial_call=True
)
def save_record(n_clicks, date_val, record_type, category, client, description,
                currency, amount, ttm, withholding, withholding_amount,
                proration, proration_rate, edit_id, attachment_data, attachment_name,
                auth_session):
    """Save record to database and close modal."""
    if not n_clicks or not date_val or not record_type or not category or not amount:
        raise PreventUpdate

    ensure_session_from_auth_data(auth_session)

    try:
        # Validate and sanitize all inputs
        date_val = valid.validate_date(date_val)
        record_type = valid.validate_record_type(record_type)
        category = valid.sanitize_category(category)
        client = valid.sanitize_client(client)
        description = valid.sanitize_description(description)
        currency = valid.validate_currency(currency)
        amount = valid.validate_amount(amount, "金額")

        ttm = float(ttm) if ttm else None
        if currency == 'USD' and ttm:
            amount_jpy = calc.calculate_jpy_amount(amount, currency, ttm)
        else:
            amount_jpy = amount
        proration_rate_val = valid.validate_rate(proration_rate, "按分率") if proration_rate else 100
        if proration:
            amount_prorated = calc.calculate_prorated_amount(amount_jpy, proration_rate_val)
        else:
            amount_prorated = amount_jpy
        attachment_path = None
        if attachment_data and attachment_name:
            ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png'}
            attachment_name = valid.validate_filename(attachment_name)
            ext = valid.validate_file_extension(attachment_name, ALLOWED_EXTENSIONS)
            fiscal_year = calc.get_fiscal_year(date_val)
            year_dir = os.path.join(ATTACHMENTS_DIR, str(fiscal_year))
            os.makedirs(year_dir, exist_ok=True)
            safe_name = f"{date_val}_{record_type}_{datetime.now().strftime('%H%M%S')}{ext}"
            file_path = os.path.join(year_dir, safe_name)
            _, content_string = attachment_data.split(',')
            decoded = base64.b64decode(content_string)
            MAX_FILE_SIZE = 10 * 1024 * 1024
            if len(decoded) > MAX_FILE_SIZE:
                raise ValueError("ファイルサイズが大きすぎます（最大10MB）")
            with open(file_path, 'wb') as f:
                f.write(decoded)
            attachment_path = f"{fiscal_year}/{safe_name}"
        # Add category if new (category is already sanitized)
        db.add_category(record_type, category)
        record = {
            'date': date_val,
            'type': record_type,
            'category': category,
            'client': client,
            'description': description,
            'currency': currency,
            'amount_original': amount,
            'ttm': ttm,
            'amount_jpy': amount_jpy,
            'withholding_tax': bool(withholding),
            'withholding_amount': float(withholding_amount) if withholding_amount else 0,
            'proration': bool(proration),
            'proration_rate': proration_rate_val,
            'amount_prorated': amount_prorated,
            'attachment_path': attachment_path,
            'fiscal_year': calc.get_fiscal_year(date_val)
        }
        if edit_id:
            db.update_record(edit_id, record)
            message = "記録を更新しました"
        else:
            db.save_record(record)
            message = "記録を保存しました"
        # 保存成功時：テーブル更新、トースト表示、モーダルを閉じる
        return datetime.now().isoformat(), message, True, "成功", False, None
    except (ValueError, valid.ValidationError) as e:
        # バリデーションエラー時：モーダルは開いたまま
        return no_update, f"入力エラー: {str(e)}", True, "入力エラー", no_update, no_update
    except IOError:
        return no_update, "ファイルの保存に失敗しました", True, "ファイルエラー", no_update, no_update
    except Exception:
        import logging
        logging.exception("Record save failed")
        return no_update, "予期しないエラーが発生しました", True, "エラー", no_update, no_update


@app.callback(
    [Output('store-records-data', 'data', allow_duplicate=True),
     Output('toast-notification', 'children', allow_duplicate=True),
     Output('toast-notification', 'is_open', allow_duplicate=True),
     Output('toast-notification', 'header', allow_duplicate=True)],
    Input('btn-delete-selected', 'n_clicks'),
    [State('records-table', 'selected_rows'),
     State('records-table', 'data'),
     State('store-auth-session', 'data')],
    prevent_initial_call=True
)
def delete_records(n_clicks, selected_rows, table_data, auth_session):
    """Delete selected records."""
    if not n_clicks or not selected_rows or not table_data:
        raise PreventUpdate

    ensure_session_from_auth_data(auth_session)

    deleted_count = 0
    for idx in selected_rows:
        record_id = table_data[idx].get('id')
        if record_id and db.delete_record(record_id):
            deleted_count += 1
    return datetime.now().isoformat(), f"{deleted_count}件の記録を削除しました", True, "削除完了"


# =============================================================================
# Export Callbacks
# =============================================================================

@app.callback(
    Output('download-csv', 'data'),
    Input('btn-download-csv', 'n_clicks'),
    [State('records-year', 'value'),
     State('store-auth-session', 'data')],
    prevent_initial_call=True
)
def download_csv(n_clicks, year, auth_session):
    """Download records as raw CSV (all fields including attachment path)."""
    if not n_clicks or not year:
        raise PreventUpdate

    ensure_session_from_auth_data(auth_session)
    csv_content = db.export_raw_records_to_csv(int(year))
    return dict(content=csv_content, filename=f"tax_records_{year}.csv")


@app.callback(
    [Output('download-attachments-zip', 'data'),
     Output('toast-notification', 'children', allow_duplicate=True),
     Output('toast-notification', 'is_open', allow_duplicate=True),
     Output('toast-notification', 'header', allow_duplicate=True)],
    Input('btn-download-attachments', 'n_clicks'),
    [State('records-year', 'value'),
     State('store-auth-session', 'data')],
    prevent_initial_call=True
)
def download_attachments(n_clicks, year, auth_session):
    """Download all attachments for the selected year as a ZIP file."""
    if not n_clicks or not year:
        raise PreventUpdate

    ensure_session_from_auth_data(auth_session)
    year = int(year)

    # Get attachments with metadata for this year
    attachments = db.get_attachments_with_metadata(year)

    if not attachments:
        return no_update, "この年度には添付ファイルがありません", True, "情報"

    # Download and create ZIP (organized by month)
    zip_data = storage.download_all_attachments_as_zip(year, attachments)

    if not zip_data:
        return no_update, "添付ファイルのダウンロードに失敗しました", True, "エラー"

    # Encode as base64 for download
    zip_base64 = base64.b64encode(zip_data).decode('utf-8')

    return (
        dict(
            content=zip_base64,
            filename=f"attachments_{year}.zip",
            base64=True
        ),
        f"{len(attachments)}件の添付ファイルをダウンロードしました",
        True,
        "ダウンロード完了"
    )


# =============================================================================
# File Upload Callbacks
# =============================================================================

@app.callback(
    [Output('upload-preview', 'children'),
     Output('store-attachment-data', 'data'),
     Output('store-attachment-name', 'data')],
    Input('upload-file', 'contents'),
    State('upload-file', 'filename'),
    prevent_initial_call=True
)
def handle_upload(contents, filename):
    """Handle file upload."""
    if not contents:
        raise PreventUpdate
    ext = os.path.splitext(filename)[1].lower()
    if ext == '.pdf':
        preview = html.Div([
            html.I(className="fas fa-file-pdf fa-2x text-danger"),
            html.P(filename, className="mt-2 mb-0")
        ], className="text-center p-3 border rounded")
    else:
        preview = html.Img(src=contents, className="preview-image")
    return preview, contents, filename


# =============================================================================
# Gemini AI Callbacks
# =============================================================================

@app.callback(
    [Output('gemini-status', 'children'),
     Output('input-date', 'value', allow_duplicate=True),
     Output('input-type', 'value', allow_duplicate=True),
     Output('input-category', 'value', allow_duplicate=True),
     Output('input-client', 'value', allow_duplicate=True),
     Output('input-description', 'value', allow_duplicate=True),
     Output('input-currency', 'value', allow_duplicate=True),
     Output('input-amount', 'value', allow_duplicate=True)],
    Input('btn-gemini', 'n_clicks'),
    [State('store-attachment-data', 'data'),
     State('store-attachment-name', 'data')],
    prevent_initial_call=True
)
def process_with_gemini(n_clicks, attachment_data, attachment_name):
    """Process attachment with Gemini API and auto-fill form fields."""
    # Default: no updates to form fields
    no_updates = [no_update] * 7

    if not n_clicks or not attachment_data or not attachment_name:
        return ["添付ファイルがありません"] + no_updates
    if not gemini.is_gemini_configured():
        return ["APIキーが設定されていません（環境変数 GEMINI_API_KEY を設定してください）"] + no_updates
    try:
        _, content_string = attachment_data.split(',')
        decoded = base64.b64decode(content_string)
        result = gemini.process_attachment(decoded, attachment_name)
        if result.get('success'):
            # Extract values from Gemini result
            extracted_date = result.get('date') or no_update
            extracted_type = result.get('type') or no_update
            extracted_category = result.get('category') or no_update
            extracted_client = result.get('client') or no_update
            extracted_description = result.get('description') or no_update
            extracted_currency = result.get('currency') or no_update
            extracted_amount = result.get('amount') or no_update

            status_message = html.Div([
                html.I(className="fas fa-check-circle text-success me-2"),
                "解析完了！フォームに自動入力しました"
            ], className="text-success")

            return [
                status_message,
                extracted_date,
                extracted_type,
                extracted_category,
                extracted_client,
                extracted_description,
                extracted_currency,
                extracted_amount
            ]
        else:
            return [f"解析エラー: {result.get('error', '不明なエラー')}"] + no_updates
    except Exception as e:
        return [f"エラー: {str(e)}"] + no_updates


# =============================================================================
# Clientside Callback for Form Validation
# =============================================================================

# Clientside callback for form validation before save
app.clientside_callback(
    """
    function(n_clicks) {
        if (!n_clicks) return window.dash_clientside.no_update;

        var form = document.getElementById('record-form');
        if (form && !form.checkValidity()) {
            form.reportValidity();
            return window.dash_clientside.no_update;
        }
        return n_clicks;
    }
    """,
    Output('btn-save', 'n_clicks'),
    Input('btn-save', 'n_clicks'),
    prevent_initial_call=True
)
