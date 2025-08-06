import requests
from app.utils import load_settings


class GraphAPIError(Exception):
    """Excepción para errores de Microsoft Graph."""

    def __init__(self, status_code, message):
        messages = {
            400: 'Solicitud inválida',
            401: 'Credenciales inválidas o sin permisos',
            403: 'Acceso denegado',
            404: 'Recurso no encontrado',
        }
        msg = messages.get(status_code, message)
        super().__init__(f"Graph API error {status_code}: {msg}")
        self.status_code = status_code
        self.message = msg


def get_access_token(cfg=None):
    """Obtiene un token de acceso usando client_credentials."""
    if cfg is None:
        cfg = load_settings().get('onedrive', {})
    url = f"https://login.microsoftonline.com/{cfg.get('tenant_id')}/oauth2/v2.0/token"
    data = {
        'client_id': cfg.get('client_id'),
        'scope': 'https://graph.microsoft.com/.default',
        'client_secret': cfg.get('client_secret'),
        'grant_type': 'client_credentials',
    }
    response = requests.post(url, data=data)
    if response.status_code >= 400:
        raise GraphAPIError(response.status_code, response.text)
    return response.json().get('access_token')
