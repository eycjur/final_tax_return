"""Tax Return Record Application - Main entry point."""
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output, State

from app import app
from components.common import get_navbar

# Import all pages to register their callbacks
from pages import records, report, settings

# Main layout
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),

    # Data stores
    dcc.Store(id='store-api-key', storage_type='local'),
    dcc.Store(id='store-edit-id', storage_type='memory'),
    dcc.Store(id='store-attachment-data', storage_type='memory'),
    dcc.Store(id='store-attachment-name', storage_type='memory'),
    dcc.Store(id='store-records-data', storage_type='memory'),

    # Navigation
    get_navbar(),

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


# Routing callback
@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    """Route to appropriate page based on URL."""
    if pathname == '/report':
        return report.layout()
    elif pathname == '/settings':
        return settings.layout()
    else:
        # Default to records page (including '/' and '/records')
        return records.layout()


# API key clientside callback (for settings page)
app.clientside_callback(
    """
    function(n_clicks, stored_key, api_key) {
        var ctx = window.dash_clientside.callback_context;
        var triggered = ctx.triggered[0];
        var noUpdate = window.dash_clientside.no_update;

        // トリガーを確認
        var triggerId = triggered ? triggered.prop_id.split('.')[0] : '';
        var triggerValue = triggered ? triggered.value : null;

        // 保存ボタンがクリックされた場合（実際のクリックのみ）
        if (triggerId === 'btn-save-api-key' && triggerValue && triggerValue > 0) {
            // 空の場合は保存しない
            if (!api_key || api_key.trim() === '') {
                return [noUpdate, noUpdate, noUpdate, noUpdate];
            }

            // 暗号化して保存
            var encrypted = window.CryptoUtils.encrypt(api_key);
            return ['APIキーを保存しました', encrypted, '', '************（保存済み）'];
        }

        // store-api-keyが更新された場合、または初期ロード時
        // 保存済みキーがあれば placeholder を更新
        if (stored_key && stored_key.length > 0) {
            return [noUpdate, noUpdate, '', '************（保存済み）'];
        }

        // キーが未保存の場合
        return [noUpdate, noUpdate, '', 'Gemini APIキーを入力'];
    }
    """,
    [Output('api-key-status', 'children'),
     Output('store-api-key', 'data'),
     Output('input-api-key', 'value'),
     Output('input-api-key', 'placeholder')],
    [Input('btn-save-api-key', 'n_clicks'),
     Input('store-api-key', 'data')],
    State('input-api-key', 'value')
)


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
