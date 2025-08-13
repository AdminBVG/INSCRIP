import logging
import requests
from inscripciones.utils import load_settings


logger = logging.getLogger(__name__)


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
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
    except requests.RequestException as e:
        status = getattr(e.response, 'status_code', 0)
        text = getattr(e.response, 'text', str(e))
        logger.exception("Error obteniendo token de Graph")
        raise GraphAPIError(status, text) from e
    token = response.json().get('access_token')
    if not token:
        logger.error("No se recibió el token de acceso")
        raise GraphAPIError(getattr(response, 'status_code', 0), 'Token no recibido')
    logger.info("Token de Graph obtenido")
    return token
