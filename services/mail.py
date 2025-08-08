import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.utils import load_settings

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


def send_mail(nombre, categoria, fields, file_links, recipients=None):
    user, password, host, port = _get_cfg()
    if recipients:
        if isinstance(recipients, str):
            recipients = [r.strip() for r in recipients.split(',') if r.strip()]
    else:
        recipients = [user]
    subject = f"Inscripción recibida: {nombre} - {categoria}"
    body = "<p>Se ha recibido una inscripción con los siguientes datos:</p><ul>"
    for label, value in fields.items():
        body += f"<li><strong>{label}:</strong> {value}</li>"
    body += "</ul><p>Archivos:</p><ul>"
    for link in file_links:
        body += f"<li><a href='{link}'>{link}</a></li>"
    body += "</ul>"
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = user
    msg['To'] = ", ".join(recipients)
    msg.attach(MIMEText(body, 'html'))
    try:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
        return True
    except Exception as e:
        logger.exception("Error enviando correo")
        raise RuntimeError(f"Error enviando correo: {e}") from e

