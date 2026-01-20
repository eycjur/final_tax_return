"""Settings page - API keys and proration presets."""
import dash_bootstrap_components as dbc
from dash import html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from app import app
from utils import database as db


def layout():
    """Create settings page layout."""
    return dbc.Container([
        html.H4("設定", className="mb-4"),

        dbc.Card([
            dbc.CardHeader("Gemini API設定"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("APIキー", html_for="input-api-key"),
                        dbc.Input(
                            type="password",
                            id="input-api-key",
                            placeholder="Gemini APIキーを入力"
                        ),
                        dbc.FormText("Google AI StudioでAPIキーを取得できます（ブラウザのlocalStorageに保存）"),
                    ], md=8),
                    dbc.Col([
                        dbc.Label("　"),
                        html.Div([
                            dbc.Button("保存", id="btn-save-api-key", color="primary", n_clicks=0),
                        ])
                    ], md=4),
                ]),
                html.Div(id="api-key-status", className="mt-2")
            ])
        ], className="mb-4"),

        dbc.Card([
            dbc.CardHeader("按分率プリセット"),
            dbc.CardBody([
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
                dbc.Button("保存", id="btn-save-presets", color="primary"),
                html.Div(id="preset-status", className="mt-2")
            ])
        ]),
    ], fluid=True)


@app.callback(
    Output('preset-status', 'children'),
    Input('btn-save-presets', 'n_clicks'),
    [State('preset-rent-rate', 'value'),
     State('preset-comm-rate', 'value'),
     State('preset-utility-rate', 'value')],
    prevent_initial_call=True
)
def save_presets(n_clicks, rent, comm, utility):
    """Save proration presets."""
    if not n_clicks:
        raise PreventUpdate
    db.save_setting('preset_rent_rate', str(rent or 50))
    db.save_setting('preset_comm_rate', str(comm or 50))
    db.save_setting('preset_utility_rate', str(utility or 30))
    return dbc.Alert("按分率を保存しました", color="success", duration=3000)
