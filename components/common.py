"""Common UI components shared across pages."""
from datetime import datetime

import dash_bootstrap_components as dbc
from dash import html, dcc

from app import AUTH_ENABLED
from utils import calculations as calc

CURRENT_YEAR = datetime.now().year
YEARS = list(range(CURRENT_YEAR - 5, CURRENT_YEAR + 2))


def get_user_menu():
    """Create user menu placeholder for navbar (only when auth is enabled).

    The actual content is rendered by a callback in index.py based on session data.
    """
    if not AUTH_ENABLED:
        return None

    return html.Div(id="navbar-user-menu")


def get_navbar():
    """Create navigation bar."""
    user_menu = get_user_menu()

    nav_items = [
        dbc.NavItem(dbc.NavLink("収支記録", href="/", active="exact")),
        dbc.NavItem(dbc.NavLink("レポート", href="/report", active="exact")),
    ]

    return dbc.Navbar(
        dbc.Container([
            dbc.NavbarBrand([
                html.I(className="fas fa-calculator me-2"),
                "確定申告収支記録"
            ], href="/", className="fs-5"),
            dbc.Nav(nav_items, className="ms-auto", navbar=True),
            user_menu if user_menu else html.Div(),
        ], fluid=True),
        color="white",
        className="mb-4"
    )


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
        ], md=3),
        dbc.Col([
            dbc.Card([
                html.Div([
                    html.Div(calc.format_currency(summary['total_expense']), className="value"),
                    html.Div("経費合計", className="label")
                ], className="summary-card expense")
            ])
        ], md=3),
        dbc.Col([
            dbc.Card([
                html.Div([
                    html.Div(calc.format_currency(summary['net_income']), className="value"),
                    html.Div("所得金額", className="label")
                ], className="summary-card net")
            ])
        ], md=3),
        dbc.Col([
            dbc.Card([
                html.Div([
                    html.Div(calc.format_currency(summary['total_withholding']), className="value"),
                    html.Div("源泉徴収額", className="label")
                ], className="summary-card")
            ])
        ], md=3),
    ], className="mb-4")
