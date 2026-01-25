"""Record form component for tax records."""
from datetime import date

import dash_bootstrap_components as dbc
from dash import dcc, html

from utils import database as db


def create_record_form(record: dict | None = None):
    """Create the record input form.

    Args:
        record: Optional dict with existing record data for editing.

    Returns:
        dbc.Form component with all input fields.
    """
    record = record or {}
    clients = db.get_clients()

    return dbc.Form(id="record-form", children=[
        dbc.Row([
            dbc.Col([
                dbc.Label(["日付", html.Span("*", className="text-danger ms-1")], html_for="input-date"),
                dbc.Input(
                    type="date",
                    id="input-date",
                    value=record.get('date', date.today().isoformat()),
                    required=True
                )
            ], md=4),
            dbc.Col([
                dbc.Label(["種別", html.Span("*", className="text-danger ms-1")], html_for="input-type"),
                dbc.Select(
                    id="input-type",
                    options=[
                        {'label': '収入', 'value': 'income'},
                        {'label': '支出', 'value': 'expense'}
                    ],
                    value=record.get('type', 'expense'),
                    required=True
                )
            ], md=4),
            dbc.Col([
                dbc.Label(["カテゴリ", html.Span("*", className="text-danger ms-1")], html_for="input-category"),
                html.Div([
                    dbc.Input(
                        type="text",
                        id="input-category",
                        value=record.get('category', ''),
                        placeholder="選択または入力",
                        list="category-datalist",
                        required=True
                    ),
                    html.Datalist(id="category-datalist", children=[])
                ])
            ], md=4),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col([
                dbc.Label("取引先", html_for="input-client"),
                html.Div([
                    dbc.Input(
                        type="text",
                        id="input-client",
                        value=record.get('client', ''),
                        placeholder="選択または入力",
                        list="client-datalist"
                    ),
                    html.Datalist(
                        id="client-datalist",
                        children=[html.Option(value=c) for c in clients]
                    )
                ])
            ], md=6),
            dbc.Col([
                dbc.Label("摘要", html_for="input-description"),
                html.Div([
                    dbc.Input(
                        type="text",
                        id="input-description",
                        value=record.get('description', ''),
                        placeholder="内容の説明",
                        list="description-datalist"
                    ),
                    html.Datalist(
                        id="description-datalist",
                        children=[html.Option(value=d) for d in db.get_descriptions()]
                    )
                ])
            ], md=6),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col([
                dbc.Label("通貨", html_for="input-currency"),
                dbc.Select(
                    id="input-currency",
                    options=[
                        {'label': '日本円 (JPY)', 'value': 'JPY'},
                        {'label': '米ドル (USD)', 'value': 'USD'}
                    ],
                    value=record.get('currency', 'JPY')
                )
            ], md=3),
            dbc.Col([
                dbc.Label(["金額", html.Span("*", className="text-danger ms-1")], html_for="input-amount"),
                dbc.Input(
                    type="number",
                    id="input-amount",
                    value=record.get('amount_original', ''),
                    placeholder="0",
                    required=True,
                    min=0
                )
            ], md=3),
            dbc.Col([
                dbc.Label("TTMレート", html_for="input-ttm"),
                dbc.Input(
                    type="number",
                    id="input-ttm",
                    value=record.get('ttm', ''),
                    placeholder="例: 150.00",
                    step="0.01",
                    disabled=True
                ),
                html.Small(
                    id="ttm-lookup-link",
                    className="text-muted"
                )
            ], md=3),
            dbc.Col([
                dbc.Label("円換算額", html_for="display-jpy"),
                dbc.Input(
                    type="text",
                    id="display-jpy",
                    value='',
                    disabled=True
                )
            ], md=3),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col([
                dbc.Checkbox(
                    id="input-withholding",
                    label="源泉徴収あり",
                    value=bool(record.get('withholding_tax', 0))
                ),
            ], md=3),
            dbc.Col([
                dbc.Label("源泉徴収額", html_for="input-withholding-amount"),
                dbc.Input(
                    type="number",
                    id="input-withholding-amount",
                    value=record.get('withholding_amount', ''),
                    placeholder="自動計算または手入力",
                    disabled=True
                )
            ], md=3),
            dbc.Col([
                dbc.Checkbox(
                    id="input-proration",
                    label="按分対象",
                    value=bool(record.get('proration', 0))
                ),
            ], md=2),
            dbc.Col([
                dbc.Label("按分率 (%)", html_for="input-proration-rate"),
                dbc.Input(
                    type="number",
                    id="input-proration-rate",
                    value=record.get('proration_rate', 100),
                    min=0,
                    max=100,
                    disabled=True
                )
            ], md=2),
            dbc.Col([
                dbc.Label("按分後金額", html_for="display-prorated"),
                dbc.Input(
                    type="text",
                    id="display-prorated",
                    value='',
                    disabled=True
                )
            ], md=2),
        ], className="mb-3"),

        html.Hr(),

        dbc.Row([
            dbc.Col([
                dbc.Label("添付ファイル"),
                dcc.Upload(
                    id="upload-file",
                    children=html.Div([
                        html.I(className="fas fa-cloud-upload-alt fa-2x mb-2"),
                        html.Br(),
                        "ファイルをドラッグ＆ドロップ",
                        html.Br(),
                        "またはクリックして選択",
                        html.Br(),
                        html.Small("(PDF, JPG, PNG)", className="text-muted")
                    ], className="upload-area"),
                    multiple=False,
                    accept=".pdf,.jpg,.jpeg,.png"
                ),
                html.Div(id="upload-preview", className="mt-2"),
            ], md=6),
            dbc.Col([
                dbc.Label("カメラで撮影"),
                html.Div([
                    html.Button([
                        html.I(className="fas fa-camera me-2"),
                        "カメラを起動"
                    ], id="btn-camera", className="camera-btn mb-2"),
                    html.Div(id="camera-container", style={'display': 'none'}, children=[
                        html.Video(id="camera-video", autoPlay=True, style={'width': '100%', 'maxWidth': '400px', 'borderRadius': '8px'}),
                        html.Br(),
                        html.Button([
                            html.I(className="fas fa-circle me-2"),
                            "撮影"
                        ], id="btn-capture", className="btn btn-danger mt-2 me-2"),
                        html.Button([
                            html.I(className="fas fa-times me-2"),
                            "キャンセル"
                        ], id="btn-camera-cancel", className="btn btn-secondary mt-2"),
                    ]),
                    html.Canvas(id="camera-canvas", style={'display': 'none'}),
                    html.Div(id="camera-preview", className="mt-2"),
                ]),
            ], md=6),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col([
                dbc.Button([
                    html.I(className="fas fa-magic me-2"),
                    "Geminiで自動入力"
                ], id="btn-gemini", color="info", outline=True, className="me-2"),
                dbc.Spinner(html.Span(id="gemini-status"), size="sm", color="info"),
            ])
        ]),
    ])
