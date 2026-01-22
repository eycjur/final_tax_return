"""Settings page - User settings and configuration."""
import dash_bootstrap_components as dbc
from dash import html, dcc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from app import app, AUTH_ENABLED
from utils import database as db
from utils.supabase_client import ensure_session_from_auth_data


def layout():
    """Create settings page layout."""
    return dbc.Container([
        html.H4([
            html.I(className="fas fa-cog me-2"),
            "設定"
        ], className="mb-4"),

        # Account section (shown when auth is enabled)
        html.Div(id="settings-account-section"),

        # Proration presets
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-percentage me-2"),
                "按分率プリセット"
            ]),
            dbc.CardBody([
                html.P(
                    "経費の按分率のデフォルト値を設定できます。",
                    className="text-muted mb-3"
                ),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("家賃按分率 (%)"),
                        dbc.Input(
                            type="number",
                            id="preset-rent-rate",
                            value=db.get_setting('preset_rent_rate', '50'),
                            min=0, max=100
                        )
                    ], md=4),
                    dbc.Col([
                        dbc.Label("通信費按分率 (%)"),
                        dbc.Input(
                            type="number",
                            id="preset-comm-rate",
                            value=db.get_setting('preset_comm_rate', '50'),
                            min=0, max=100
                        )
                    ], md=4),
                    dbc.Col([
                        dbc.Label("光熱費按分率 (%)"),
                        dbc.Input(
                            type="number",
                            id="preset-utility-rate",
                            value=db.get_setting('preset_utility_rate', '30'),
                            min=0, max=100
                        )
                    ], md=4),
                ], className="mb-3"),
                dbc.Button([
                    html.I(className="fas fa-save me-2"),
                    "保存"
                ], id="btn-save-presets", color="primary"),
                html.Div(id="preset-status", className="mt-2")
            ])
        ]),
    ], fluid=True)


@app.callback(
    Output('settings-account-section', 'children'),
    Input('store-auth-session', 'data')
)
def update_account_section(session):
    """Update account section based on auth state."""
    if not AUTH_ENABLED or not session:
        return html.Div()

    user = session.get('user', {})
    name = user.get('name') or user.get('email', '')
    email = user.get('email', '')
    picture = user.get('picture', '')

    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-user me-2"),
            "アカウント"
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Img(
                        src=picture if picture else "https://www.gravatar.com/avatar/?d=mp",
                        className="rounded-circle",
                        height="64px",
                        width="64px",
                        style={"objectFit": "cover"}
                    ),
                ], width="auto"),
                dbc.Col([
                    html.H5(name, className="mb-1"),
                    html.P(email, className="text-muted mb-0"),
                ], className="d-flex flex-column justify-content-center"),
                dbc.Col([
                    dbc.Button([
                        html.I(className="fas fa-sign-out-alt me-2"),
                        "ログアウト"
                    ], id="btn-settings-logout", color="outline-danger", size="sm")
                ], width="auto", className="d-flex align-items-center"),
            ], className="align-items-center"),
        ])
    ], className="mb-4")


@app.callback(
    Output('preset-status', 'children'),
    Input('btn-save-presets', 'n_clicks'),
    [State('preset-rent-rate', 'value'),
     State('preset-comm-rate', 'value'),
     State('preset-utility-rate', 'value'),
     State('store-auth-session', 'data')],
    prevent_initial_call=True
)
def save_presets(n_clicks, rent, comm, utility, auth_session):
    """Save proration presets."""
    if not n_clicks:
        raise PreventUpdate

    ensure_session_from_auth_data(auth_session)
    db.save_setting('preset_rent_rate', str(rent or 50))
    db.save_setting('preset_comm_rate', str(comm or 50))
    db.save_setting('preset_utility_rate', str(utility or 30))
    return dbc.Alert([
        html.I(className="fas fa-check me-2"),
        "按分率を保存しました"
    ], color="success", duration=3000)


# Logout button callback
app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks > 0 && window.SupabaseAuth) {
            window.SupabaseAuth.signOut();
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output('btn-settings-logout', 'n_clicks'),
    Input('btn-settings-logout', 'n_clicks'),
    prevent_initial_call=True
)
