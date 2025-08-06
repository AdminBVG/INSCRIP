import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.utils import load_settings


def _get_cfg():
    cfg = load_settings().get('mail', {})
    user = cfg.get('mail_user')
    password = cfg.get('mail_password')
    host = cfg.get('smtp_host', 'smtp.office365.com')
    port = cfg.get('smtp_port', 587)
    if not user or not password:
        raise ValueError('Correo no configurado')
    return user, password, host, port


def test_connection() -> None:
    user, password, host, port = _get_cfg()
    msg = MIMEText('Prueba de envío de correo.')
    msg['Subject'] = 'Prueba de correo'
    msg['From'] = user
    msg['To'] = user
    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)


def send_mail(nombre, categoria, fields, file_links):
    user, password, host, port = _get_cfg()
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
    msg['To'] = user
    msg.attach(MIMEText(body, 'html'))
    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)

