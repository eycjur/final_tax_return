"""Login page for Supabase authentication."""
import dash_bootstrap_components as dbc
from dash import Input, Output, html

from app import app


def layout():
    """Create login page layout."""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-file-invoice-dollar fa-3x text-primary mb-3"),
                        ], className="text-center"),

                        html.H3("確定申告収支記録", className="text-center mb-4"),

                        html.P(
                            "個人事業主・フリーランス向けの確定申告用収支記録アプリケーションです。",
                            className="text-muted text-center mb-4"
                        ),

                        html.Hr(),

                        html.Div([
                            dbc.Button([
                                html.Img(
                                    src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg",
                                    height="20px",
                                    className="me-2"
                                ),
                                "Googleでログイン"
                            ],
                                id="btn-google-login",
                                color="light",
                                className="w-100 border",
                                n_clicks=0
                            ),
                        ], className="d-grid gap-2"),

                        html.Div([
                            html.Small([
                                "ログインすることで、",
                                html.A("利用規約", href="/terms", className="text-decoration-none"),
                                "と",
                                html.A("プライバシーポリシー", href="/privacy", className="text-decoration-none"),
                                "に同意したものとみなされます。"
                            ], className="text-muted")
                        ], className="text-center mt-4"),
                    ])
                ], className="shadow-sm")
            ], md=6, lg=4, className="mx-auto")
        ], className="min-vh-100 align-items-center")
    ], fluid=True)


def layout_logged_in(user):
    """Create logged-in state layout with user info."""
    # Handle both dict and object-like user
    if isinstance(user, dict):
        name = user.get('name', '') or user.get('email', '')
        email = user.get('email', '')
        picture = user.get('picture', '')
    else:
        name = getattr(user, 'name', '') or getattr(user, 'email', '')
        email = getattr(user, 'email', '')
        picture = getattr(user, 'picture', '')

    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.Img(
                                src=picture if picture else "https://www.gravatar.com/avatar/?d=mp",
                                className="rounded-circle mb-3",
                                height="80px"
                            ),
                        ], className="text-center"),

                        html.H5(name, className="text-center mb-2"),
                        html.P(email, className="text-muted text-center mb-4"),

                        html.Div([
                            dbc.Button([
                                html.I(className="fas fa-home me-2"),
                                "アプリに戻る"
                            ],
                                href="/",
                                color="primary",
                                className="w-100 mb-2"
                            ),
                            dbc.Button([
                                html.I(className="fas fa-sign-out-alt me-2"),
                                "ログアウト"
                            ],
                                id="btn-logout",
                                color="outline-secondary",
                                className="w-100",
                                n_clicks=0
                            ),
                        ], className="d-grid gap-2"),
                    ])
                ], className="shadow-sm")
            ], md=6, lg=4, className="mx-auto")
        ], className="min-vh-100 align-items-center")
    ], fluid=True)


# Clientside callback for Google login
app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks > 0 && window.SupabaseAuth) {
            window.SupabaseAuth.signInWithGoogle();
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output('btn-google-login', 'n_clicks'),
    Input('btn-google-login', 'n_clicks'),
    prevent_initial_call=True
)

# Clientside callback for logout
app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks > 0 && window.SupabaseAuth) {
            window.SupabaseAuth.signOut();
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output('btn-logout', 'n_clicks'),
    Input('btn-logout', 'n_clicks'),
    prevent_initial_call=True
)
