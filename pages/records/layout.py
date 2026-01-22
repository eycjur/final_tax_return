"""Layout components for the records page."""
import dash_bootstrap_components as dbc
from dash import dash_table, dcc, html

from components.common import create_summary_cards, get_year_selector
from utils import calculations as calc

from .form import create_record_form


def layout():
    """Create records list page layout with summary cards."""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H4("収支記録", className="mb-0"),
            ], md=3),
            dbc.Col([
                dbc.Row([
                    dbc.Col([get_year_selector("records-year")], md=3),
                    dbc.Col([
                        dbc.Select(
                            id="records-type-filter",
                            options=[
                                {'label': 'すべて', 'value': 'all'},
                                {'label': '収入のみ', 'value': 'income'},
                                {'label': '支出のみ', 'value': 'expense'}
                            ],
                            value='all'
                        )
                    ], md=3),
                    dbc.Col([
                        dbc.Button([
                            html.I(className="fas fa-plus me-2"),
                            "新規記録"
                        ], id="btn-new-record", color="primary")
                    ], md=3),
                    dbc.Col([
                        dbc.ButtonGroup([
                            dbc.Button([
                                html.I(className="fas fa-file-csv me-1"),
                                "CSV"
                            ], id="btn-download-csv", color="secondary", outline=True, size="sm"),
                            dbc.Button([
                                html.I(className="fas fa-file-archive me-1"),
                                "添付"
                            ], id="btn-download-attachments", color="secondary", outline=True, size="sm",
                               title="添付ファイルを一括ダウンロード"),
                        ])
                    ], md=3),
                ], className="g-2")
            ], md=9),
        ], className="mb-4 align-items-center"),

        # Summary cards
        html.Div(id="records-summary"),

        dbc.Row([
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button([
                        html.I(className="fas fa-edit me-1"),
                        "編集"
                    ], id="btn-edit-selected", color="primary", outline=True, size="sm"),
                    dbc.Button([
                        html.I(className="fas fa-copy me-1"),
                        "複製"
                    ], id="btn-duplicate-selected", color="info", outline=True, size="sm"),
                    dbc.Button([
                        html.I(className="fas fa-trash me-1"),
                        "削除"
                    ], id="btn-delete-selected", color="danger", outline=True, size="sm"),
                ], className="mb-3")
            ])
        ]),

        dbc.Card([
            dbc.CardBody([
                # Empty state message (shown when no records)
                html.Div(
                    id="records-empty-state",
                    children=[
                        html.I(className="fas fa-inbox fa-3x text-muted mb-3"),
                        html.P("記録がありません", className="text-muted")
                    ],
                    className="text-center py-5",
                    style={'display': 'none'}
                ),
                # DataTable (always present)
                dash_table.DataTable(
                    id='records-table',
                    columns=[
                        {'name': '日付', 'id': 'date'},
                        {'name': '種別', 'id': 'type_display'},
                        {'name': 'カテゴリ', 'id': 'category'},
                        {'name': '取引先', 'id': 'client'},
                        {'name': '摘要', 'id': 'description'},
                        {'name': '金額', 'id': 'amount_display'},
                        {'name': '按分後', 'id': 'prorated_display'},
                    ],
                    data=[],
                    row_selectable='multi',
                    selected_rows=[],
                    page_size=20,
                    style_table={'overflowX': 'auto'},
                    style_cell={
                        'textAlign': 'left',
                        'padding': '12px',
                        'fontSize': '14px'
                    },
                    style_header={
                        'backgroundColor': '#f1f5f9',
                        'fontWeight': '600',
                        'color': '#64748b'
                    },
                    style_data_conditional=[
                        {
                            'if': {'filter_query': '{type} = income'},
                            'backgroundColor': '#f0fdf4'
                        },
                        {
                            'if': {'filter_query': '{type} = expense'},
                            'backgroundColor': '#fef2f2'
                        }
                    ],
                    style_as_list_view=True,
                ),
            ])
        ]),

        dcc.Download(id="download-csv"),
        dcc.Download(id="download-attachments-zip"),
    ], fluid=True)


def get_form_modal():
    """Create the record form modal."""
    return dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle(id="modal-title")),
        dbc.ModalBody(id="modal-body"),
        dbc.ModalFooter([
            dbc.Button([
                html.I(className="fas fa-save me-2"),
                "保存"
            ], id="btn-save", color="primary", className="me-2"),
            dbc.Button([
                html.I(className="fas fa-times me-2"),
                "キャンセル"
            ], id="btn-cancel", color="secondary", outline=True, n_clicks=0),
        ]),
    ], id="form-modal", size="xl", is_open=False, backdrop="static")
