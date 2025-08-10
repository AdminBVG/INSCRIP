import logging
import smtplib
from email.mime.text import MIMEText
import requests

from app.utils import load_settings
from .graph_auth import GraphAPIError

logger = logging.getLogger(__name__)


def _get_cfg():
    cfg = load_settings().get('mail', {})
    user = cfg.get('mail_user')
    password = cfg.get('mail_password')
    host = cfg.get('smtp_host', 'smtp.office365.com')
    port = cfg.get('smtp_port', 587)
    if not user or not password:
        raise ValueError('Correo no configurado')
    return user, password, host, port


def test_connection(
    user: str | None = None,
    password: str | None = None,
    host: str = 'smtp.office365.com',
    port: int = 587,
) -> None:
    if user is None or password is None:
        user, password, host, port = _get_cfg()
    msg = MIMEText('Prueba de envío de correo.')
    msg['Subject'] = 'Prueba de correo'
    msg['From'] = user
    msg['To'] = user
    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)


def send_mail(token, user_id, nombre, categoria, fields, file_links, to_recipients, cc_recipients=None):
    """Envía un correo usando Microsoft Graph."""
    if cc_recipients is None:
        cc_recipients = []
    url = f"https://graph.microsoft.com/v1.0/users/{user_id}/sendMail"
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    body = "<p>Se ha recibido una inscripción con los siguientes datos:</p><ul>"
    for label, value in fields.items():
        body += f"<li><strong>{label}:</strong> {value}</li>"
    body += "</ul><p>Archivos:</p><ul>"
    for link in file_links:
        body += f"<li><a href='{link}'>{link}</a></li>"
    body += "</ul>"
    msg = {
        "message": {
            "subject": f"Inscripción recibida: {nombre} - {categoria}",
            "body": {"contentType": "HTML", "content": body},
            "toRecipients": [{"emailAddress": {"address": e}} for e in to_recipients],
            "ccRecipients": [{"emailAddress": {"address": e}} for e in cc_recipients],
        },
        "saveToSentItems": "true",
    }
    try:
        response = requests.post(url, headers=headers, json=msg)
        response.raise_for_status()
    except requests.RequestException as e:
        status = getattr(e.response, 'status_code', 0)
        text = getattr(e.response, 'text', str(e))
        logger.exception("Error enviando correo")
        raise GraphAPIError(status, text) from e
    logger.info("Correo enviado: %s", ", ".join(to_recipients + cc_recipients))

