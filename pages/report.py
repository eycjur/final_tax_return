"""Report page - Tax return summary and details."""
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from app import app
from components.common import create_summary_cards, get_year_selector
from utils import calculations as calc
from utils import database as db


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
                        "レポートCSV"
                    ], id="btn-download-report", color="primary", className="ms-2")
                ], className="d-flex justify-content-end")
            ], md=6),
        ], className="mb-4 align-items-center"),

        html.Div(id="report-summary"),

        dbc.Tabs([
            dbc.Tab([
                html.Div(id="income-detail", className="pt-3")
            ], label="収入明細", tab_id="tab-income"),
            dbc.Tab([
                html.Div(id="expense-detail", className="pt-3")
            ], label="経費明細", tab_id="tab-expense"),
            dbc.Tab([
                html.Div(id="client-summary", className="pt-3")
            ], label="取引先別集計", tab_id="tab-client"),
        ], id="report-tabs", active_tab="tab-income"),

        dcc.Download(id="download-report-csv"),
    ], fluid=True)


@app.callback(
    [Output('report-summary', 'children'),
     Output('income-detail', 'children'),
     Output('expense-detail', 'children'),
     Output('client-summary', 'children')],
    Input('report-year', 'value')
)
def update_report(year):
    """Update report page."""
    if not year:
        raise PreventUpdate

    year = int(year)
    summary = db.get_summary(year)
    summary_cards = create_summary_cards(summary)

    income_df = db.get_category_summary(year, 'income')
    if not income_df.empty:
        income_df['total_display'] = income_df['total'].apply(lambda x: calc.format_currency(x))
        income_table = dbc.Table.from_dataframe(
            income_df[['category', 'count', 'total_display']].rename(columns={
                'category': 'カテゴリ',
                'count': '件数',
                'total_display': '合計'
            }),
            striped=True, bordered=True, hover=True
        )
    else:
        income_table = html.P("データがありません", className="text-muted")

    expense_df = db.get_category_summary(year, 'expense')
    if not expense_df.empty:
        expense_df['total_display'] = expense_df['total'].apply(lambda x: calc.format_currency(x))
        expense_table = dbc.Table.from_dataframe(
            expense_df[['category', 'count', 'total_display']].rename(columns={
                'category': 'カテゴリ',
                'count': '件数',
                'total_display': '合計（按分後）'
            }),
            striped=True, bordered=True, hover=True
        )
    else:
        expense_table = html.P("データがありません", className="text-muted")

    client_df = db.get_client_summary(year)
    if not client_df.empty:
        client_df['total_income_display'] = client_df['total_income'].apply(lambda x: calc.format_currency(x))
        client_df['total_withholding_display'] = client_df['total_withholding'].apply(lambda x: calc.format_currency(x))
        client_table = dbc.Table.from_dataframe(
            client_df[['client', 'count', 'total_income_display', 'total_withholding_display']].rename(columns={
                'client': '取引先',
                'count': '件数',
                'total_income_display': '収入合計',
                'total_withholding_display': '源泉徴収額'
            }),
            striped=True, bordered=True, hover=True
        )
    else:
        client_table = html.P("データがありません", className="text-muted")

    return summary_cards, income_table, expense_table, client_table


@app.callback(
    Output('download-report-csv', 'data'),
    Input('btn-download-report', 'n_clicks'),
    State('report-year', 'value'),
    prevent_initial_call=True
)
def download_report_csv(n_clicks, year):
    """Download report as CSV."""
    if not n_clicks or not year:
        raise PreventUpdate
    csv_content = db.export_to_csv(int(year))
    return {'content': csv_content, 'filename': f'tax_report_{year}.csv'}
