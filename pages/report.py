"""Report page - Tax return summary and details."""
import dash_bootstrap_components as dbc
import pandas as pd
from dash import ALL, dash_table, dcc, html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from app import app
from components.common import CURRENT_YEAR, get_year_selector
from utils import calculations as calc
from utils import database as db

# 許可された種目（カテゴリ）
ALLOWED_CATEGORIES = {'個人年金', '原稿料', '講演料', '印税', '放送出演料', '暗号資産'}


def layout():
    """Create report page layout."""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H4("確定申告レポート", className="mb-0"),
            ], md=6),
            dbc.Col([
                html.Div([
                    get_year_selector("report-year"),
                    dbc.Button([
                        html.I(className="fas fa-download me-2"),
                        html.Span("レポートCSV", id="btn-download-report-text")
                    ], id="btn-download-report", color="primary", className="ms-2"),
                    html.Div(id="download-loading", className="ms-2 d-none")
                ], className="d-flex justify-content-end")
            ], md=6),
        ], className="mb-4 align-items-center"),

        dbc.Alert([
            html.I(className="fas fa-info-circle me-2"),
            "確定申告に関する動画は",
            html.A("こちら", href="https://www.youtube.com/results?search_query=%E7%A2%BA%E5%AE%9A%E7%94%B3%E5%91%8A+%E3%83%9E%E3%83%8B%E3%83%A5%E3%82%A2%E3%83%AB", target="_blank", className="ms-1"),
            "をご参照ください。"
        ], color="info", className="mb-3"),

        dbc.Row([
            dbc.Col([
                html.H5("収入", className="mb-3"),
                dcc.Loading(
                    id="loading-income-detail",
                    type="default",
                    children=html.Div(id="income-detail")
                ),
            ], md=6),
            dbc.Col([
                html.H5("経費", className="mb-3"),
                dcc.Loading(
                    id="loading-expense-detail",
                    type="default",
                    children=html.Div(id="expense-detail")
                ),
            ], md=6),
        ], className="pt-3"),

        dcc.Download(id="download-report-csv"),
    ], fluid=True)


@app.callback(
    Output('store-report-year', 'data'),
    Input('report-year', 'value'),
    prevent_initial_call=True
)
def save_report_year(year):
    """Save selected year to localStorage."""
    if year:
        return {'year': int(year)}
    return None


@app.callback(
    Output('report-year', 'value'),
    Input('url', 'pathname'),
    [State('store-report-year', 'data'),
     State('report-year', 'value')]
)
def restore_report_year(pathname, stored_data, current_value):
    """Restore last selected year when page loads."""
    # Only restore when navigating to report page
    if pathname != '/report':
        raise PreventUpdate

    # If there's stored data, use it; otherwise use current value or default
    if stored_data and stored_data.get('year'):
        return stored_data['year']
    elif current_value:
        return current_value
    else:
        return CURRENT_YEAR


def normalize_category(category: str) -> str:
    """Normalize category name - convert non-allowed categories to 'その他（xxx）' format."""
    if category in ALLOWED_CATEGORIES:
        return category
    return f"その他（{category}）"


@app.callback(
    [Output('income-detail', 'children'),
     Output('expense-detail', 'children')],
    Input('report-year', 'value')
)
def update_report(year):
    """Update report page."""
    if not year:
        raise PreventUpdate

    year = int(year)

    # Get all records for the year
    all_records_df = db.get_records(fiscal_year=year)

    if all_records_df.empty:
        return (
            html.P("データがありません", className="text-muted"),
            html.P("データがありません", className="text-muted")
        )

    # Separate income and expense records
    income_records = all_records_df[all_records_df['type'] == 'income']
    expense_records = all_records_df[all_records_df['type'] == 'expense']

    # Process income by client
    income_cards = []
    if not income_records.empty:
        income_records = income_records.copy()
        income_records['category_normalized'] = income_records['category'].apply(normalize_category)

        # 業務該当を自動判定
        def determine_business_status(category_normalized, total_amount, client_name):
            """業務該当を自動判定する"""
            # 元のカテゴリ名を取得（「その他（xxx）」の場合は元のカテゴリ名を抽出）
            original_category = category_normalized
            if category_normalized.startswith('その他（') and category_normalized.endswith('）'):
                original_category = category_normalized[4:-1]

            # 複数年にわたって収入があるかチェック（同じ会社、同じカテゴリで）
            prev_year_records = db.get_records(fiscal_year=year - 1, record_type='income', category=original_category)
            if not prev_year_records.empty and client_name:
                prev_year_records = prev_year_records[prev_year_records['client'] == client_name]
            has_multiple_years = not prev_year_records.empty

            # 自動判定
            is_business = calc.is_business_income(original_category, total_amount, has_multiple_years)
            return '該当' if is_business else '非該当'

        # Get unique clients
        clients = income_records[income_records['client'] != '']['client'].unique()

        # Process each client
        for client_name in sorted(clients):
            client_records = income_records[income_records['client'] == client_name]
            client_address = client_records['client_address'].iloc[0] if 'client_address' in client_records.columns and not client_records['client_address'].isna().all() else ''

            # Group by category for this client
            client_income_summary = client_records.groupby('category_normalized').agg(
                count=('category_normalized', 'size'),
                total=('amount_jpy', 'sum')
            ).reset_index()
            client_income_summary['total_display'] = client_income_summary['total'].apply(lambda x: calc.format_currency(x))
            client_income_summary['is_business_display'] = client_income_summary.apply(
                lambda row: determine_business_status(row['category_normalized'], row['total'], client_name), axis=1
            )
            client_income_summary = client_income_summary.rename(columns={'category_normalized': 'category'})

            # Create card for this client
            client_card = dbc.Card([
                dbc.CardHeader([
                    html.H6(client_name, className="mb-0"),
                    html.Small(f"所在地: {client_address if client_address else '未設定'}", className="text-muted")
                ]),
                dbc.CardBody([
                    dash_table.DataTable(
                        id={'type': 'income-table', 'client': client_name},
                        columns=[
                            {'name': '種目', 'id': 'category'},
                            {'name': '件数', 'id': 'count'},
                            {'name': '合計', 'id': 'total_display'},
                            {'name': '業務該当', 'id': 'is_business_display'},
                        ],
                        data=client_income_summary[['category', 'count', 'total_display', 'is_business_display']].to_dict('records') if not client_income_summary.empty else [],
                        style_table={'overflowX': 'auto'},
                        style_cell={'textAlign': 'left', 'padding': '12px'},
                        style_header={'backgroundColor': '#f1f5f9', 'fontWeight': '600'},
                        style_data_conditional=[
                            {'if': {'row_index': 'odd'}, 'backgroundColor': '#f9fafb'}
                        ],
                    ),
                ])
            ], className="mb-3")

            income_cards.append(client_card)

    # Process expenses - aggregate across all clients
    expense_total = expense_records['amount_prorated'].sum() if not expense_records.empty else 0
    expense_clients = expense_records[expense_records['client'] != '']['client'].unique()
    expense_client_list = ' + '.join(sorted(expense_clients)) if len(expense_clients) > 0 else '（事業者なし）'

    expense_display = dbc.Card([
        dbc.CardBody([
            html.H4(f"経費合計: {calc.format_currency(expense_total)}", className="mb-3"),
            html.P(f"事業者: {expense_client_list}", className="text-muted"),
        ])
    ]) if expense_total > 0 else html.P("データがありません", className="text-muted")

    return html.Div(income_cards) if income_cards else html.P("データがありません", className="text-muted"), expense_display


@app.callback(
    [Output('btn-download-report', 'disabled'),
     Output('download-loading', 'children'),
     Output('download-loading', 'className')],
    Input('btn-download-report', 'n_clicks'),
    State('report-year', 'value'),
    prevent_initial_call=True
)
def show_download_loading(n_clicks, year):
    """Show loading spinner when download button is clicked."""
    if not n_clicks or not year:
        raise PreventUpdate
    
    # Show loading spinner and disable button
    spinner = dbc.Spinner(html.Div(), type="border", color="primary", size="sm")
    return True, spinner, 'ms-2'


@app.callback(
    Output('download-report-csv', 'data'),
    Input('btn-download-report', 'n_clicks'),
    [State('report-year', 'value'),
     State('btn-download-report', 'disabled')],
    prevent_initial_call=True
)
def download_report_csv(n_clicks, year, disabled):
    """Download report as CSV."""
    if not n_clicks or not year or not disabled:
        raise PreventUpdate
    
    csv_content = db.export_to_csv(int(year))
    return {'content': csv_content, 'filename': f'tax_report_{year}.csv'}


@app.callback(
    [Output('btn-download-report', 'disabled', allow_duplicate=True),
     Output('download-loading', 'children', allow_duplicate=True),
     Output('download-loading', 'className', allow_duplicate=True)],
    Input('download-report-csv', 'data'),
    prevent_initial_call=True
)
def hide_download_loading(download_data):
    """Hide loading spinner after download completes."""
    if download_data:
        return False, None, 'ms-2 d-none'
    raise PreventUpdate


