"""Common UI components shared across pages."""
from datetime import datetime

import dash_bootstrap_components as dbc
from dash import html

from utils import calculations as calc

CURRENT_YEAR = datetime.now().year
YEARS = list(range(2025, CURRENT_YEAR + 1))


def get_year_selector(year_id: str):
    """Create year selector component."""
    return dbc.Select(
        id=year_id,
        options=[{'label': f'{y}年度', 'value': y} for y in YEARS],
        value=CURRENT_YEAR,
        style={"minWidth": "130px"}
    )


def create_summary_cards(summary: dict):
    """Create summary cards for dashboard."""
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                html.Div([
                    html.Div(calc.format_currency(summary['total_income']), className="value"),
                    html.Div("収入合計", className="label")
                ], className="summary-card income")
            ])
        ], md=4),
        dbc.Col([
            dbc.Card([
                html.Div([
                    html.Div(calc.format_currency(summary['total_expense']), className="value"),
                    html.Div("経費合計", className="label")
                ], className="summary-card expense")
            ])
        ], md=4),
        dbc.Col([
            dbc.Card([
                html.Div([
                    html.Div(calc.format_currency(summary['net_income']), className="value"),
                    html.Div("所得金額", className="label")
                ], className="summary-card net")
            ])
        ], md=4),
    ], className="mb-4")
