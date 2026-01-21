"""Tax Return Record Application - Main entry point."""
import json

import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, clientside_callback

from app import app, server, AUTH_ENABLED, SUPABASE_URL, SUPABASE_ANON_KEY
from components.common import get_navbar

# Import all pages to register their callbacks
from pages import records, report, settings, login

# Main layout
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),

    # Auth session store (synced with Supabase JS client)
    dcc.Store(id='store-auth-session', storage_type='local'),

    # Data stores
    dcc.Store(id='store-edit-id', storage_type='memory'),
    dcc.Store(id='store-attachment-data', storage_type='memory'),
    dcc.Store(id='store-attachment-name', storage_type='memory'),
    dcc.Store(id='store-records-data', storage_type='memory'),

    # Supabase configuration (passed to JavaScript via data attributes)
    html.Div(
        id='supabase-config',
        **{
            'data-url': SUPABASE_URL,
            'data-anon-key': SUPABASE_ANON_KEY,
        },
        style={'display': 'none'}
    ) if AUTH_ENABLED else html.Div(),

    # Navigation (hidden on login page)
    html.Div(id='navbar-container'),

    # Main content area
    html.Div(id='page-content', className="container-fluid"),

    # Form modal (for records page)
    records.get_form_modal(),

    # Toast notification
    dbc.Toast(
        id="toast-notification",
        header="通知",
        is_open=False,
        dismissable=True,
        icon="success",
        duration=3000,
        style={"position": "fixed", "top": 66, "right": 10, "width": 350, "zIndex": 1050},
    ),
])


# Navbar visibility callback
@app.callback(
    Output('navbar-container', 'children'),
    [Input('url', 'pathname'),
     Input('store-auth-session', 'data')]
)
def update_navbar(pathname, session):
    """Show/hide navbar based on page and auth state."""
    if AUTH_ENABLED:
        # Hide navbar on login page
        if pathname == '/login':
            return html.Div()

        # Show navbar only if authenticated
        if not session:
            return html.Div()

    # Build navbar with user menu
    nav_items = [
        dbc.NavItem(dbc.NavLink("収支記録", href="/", active="exact")),
        dbc.NavItem(dbc.NavLink("レポート", href="/report", active="exact")),
    ]

    # Create user menu if auth is enabled
    user_menu = html.Div()
    if AUTH_ENABLED and session:
        user = session.get('user', {})
        picture = user.get('picture') or "https://www.gravatar.com/avatar/?d=mp"

        user_menu = dbc.DropdownMenu([
            dbc.DropdownMenuItem([
                html.I(className="fas fa-cog me-2"),
                "設定"
            ], href="/settings"),
            dbc.DropdownMenuItem([
                html.I(className="fas fa-sign-out-alt me-2"),
                "ログアウト"
            ], id="btn-navbar-logout", n_clicks=0),
        ],
            label=html.Img(
                src=picture,
                className="rounded-circle",
                height="32px",
                width="32px",
                style={"objectFit": "cover"}
            ),
            toggle_style={"background": "transparent", "border": "none", "padding": "0"},
            align_end=True,
            className="ms-3"
        )

    return dbc.Navbar(
        dbc.Container([
            dbc.NavbarBrand([
                html.I(className="fas fa-calculator me-2"),
                "確定申告収支記録"
            ], href="/", className="fs-5"),
            dbc.Nav(nav_items, className="ms-auto", navbar=True),
            user_menu,
        ], fluid=True),
        color="white",
        className="mb-4"
    )


# Navbar logout callback
app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks > 0 && window.SupabaseAuth) {
            window.SupabaseAuth.signOut();
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output('btn-navbar-logout', 'n_clicks'),
    Input('btn-navbar-logout', 'n_clicks'),
    prevent_initial_call=True
)


# Routing callback
@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname'),
     Input('store-auth-session', 'data')]
)
def display_page(pathname, session):
    """Route to appropriate page based on URL."""
    # Check authentication if enabled
    if AUTH_ENABLED:
        if pathname == '/login':
            if session:
                # Already logged in, show user info
                user = session.get('user', {})
                return login.layout_logged_in(user)
            return login.layout()

        # Require login for all other pages
        if not session:
            return login.layout()

    # Normal routing
    if pathname == '/report':
        return report.layout()
    elif pathname == '/settings':
        return settings.layout()
    else:
        # Default to records page (including '/' and '/records')
        return records.layout()


# Camera functionality - clientside callbacks
app.clientside_callback(
    """
    function(n_clicks) {
        if (!n_clicks) return window.dash_clientside.no_update;

        var video = document.getElementById('camera-video');
        var container = document.getElementById('camera-container');

        if (container.style.display === 'none') {
            navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
                .then(function(stream) {
                    video.srcObject = stream;
                    container.style.display = 'block';
                })
                .catch(function(err) {
                    console.error('Camera error:', err);
                    alert('カメラにアクセスできません: ' + err.message);
                });
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output('camera-container', 'style'),
    Input('btn-camera', 'n_clicks'),
    prevent_initial_call=True
)

app.clientside_callback(
    """
    function(n_clicks) {
        if (!n_clicks) return [window.dash_clientside.no_update, window.dash_clientside.no_update, window.dash_clientside.no_update];

        var video = document.getElementById('camera-video');
        var canvas = document.getElementById('camera-canvas');
        var container = document.getElementById('camera-container');

        if (video.srcObject) {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0);

            var imageData = canvas.toDataURL('image/jpeg', 0.8);

            video.srcObject.getTracks().forEach(track => track.stop());
            video.srcObject = null;
            container.style.display = 'none';

            var preview = '<img src="' + imageData + '" class="preview-image">';
            return [preview, imageData, 'camera_capture.jpg'];
        }
        return [window.dash_clientside.no_update, window.dash_clientside.no_update, window.dash_clientside.no_update];
    }
    """,
    [Output('camera-preview', 'children'),
     Output('store-attachment-data', 'data', allow_duplicate=True),
     Output('store-attachment-name', 'data', allow_duplicate=True)],
    Input('btn-capture', 'n_clicks'),
    prevent_initial_call=True
)

app.clientside_callback(
    """
    function(n_clicks) {
        if (!n_clicks) return window.dash_clientside.no_update;

        var video = document.getElementById('camera-video');
        var container = document.getElementById('camera-container');

        if (video.srcObject) {
            video.srcObject.getTracks().forEach(track => track.stop());
            video.srcObject = null;
        }
        container.style.display = 'none';
        return window.dash_clientside.no_update;
    }
    """,
    Output('camera-container', 'style', allow_duplicate=True),
    Input('btn-camera-cancel', 'n_clicks'),
    prevent_initial_call=True
)


if __name__ == '__main__':
    app.run(debug=True)
