import requests
from app.utils import load_settings
from .graph_auth import get_access_token, GraphAPIError


def test_connection() -> None:
    cfg = load_settings().get('onedrive', {})
    email = cfg.get('user_id')
    if not email:
        raise ValueError('Correo no configurado')
    token = get_access_token(cfg)
    payload = {
        "message": {
            "subject": "Prueba de correo",
            "body": {"contentType": "Text", "content": "Prueba de envío de correo."},
            "toRecipients": [{"emailAddress": {"address": email}}],
        },
        "saveToSentItems": "false",
    }
    url = f"https://graph.microsoft.com/v1.0/users/{email}/sendMail"
    r = requests.post(url, headers={'Authorization': f'Bearer {token}'}, json=payload)
    if r.status_code >= 400:
        raise GraphAPIError(r.status_code, r.text)


def send_mail(nombre, categoria, fields, file_links):
    cfg = load_settings()['onedrive']
    email = cfg.get('user_id')
    if not email:
        raise ValueError('Correo no configurado')
    token = get_access_token(cfg)
    subject = f"Inscripción recibida: {nombre} - {categoria}"
    body = "<p>Se ha recibido una inscripción con los siguientes datos:</p><ul>"
    for label, value in fields.items():
        body += f"<li><strong>{label}:</strong> {value}</li>"
    body += "</ul><p>Archivos:</p><ul>"
    for link in file_links:
        body += f"<li><a href='{link}'>{link}</a></li>"
    body += "</ul>"
    payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": body},
            "toRecipients": [{"emailAddress": {"address": email}}],
        },
        "saveToSentItems": "false",
    }
    url = f"https://graph.microsoft.com/v1.0/users/{email}/sendMail"
    r = requests.post(url, headers={'Authorization': f'Bearer {token}'}, json=payload)
    if r.status_code >= 400:
        raise GraphAPIError(r.status_code, r.text)
