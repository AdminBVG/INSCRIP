import smtplib
from email.mime.text import MIMEText
from app.utils import load_settings


SMTP_HOST = 'smtp.gmail.com'
SMTP_PORT = 587


def test_connection(email: str, password: str) -> None:
    if not email or not password:
        raise ValueError('Credenciales incompletas')
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
        server.starttls()
        server.login(email, password)
        server.noop()


def send_mail(nombre, categoria, fields, file_links):
    cfg = load_settings().get('mail', {})
    email = cfg.get('email')
    password = cfg.get('password')
    if not email or not password:
        raise ValueError('Correo no configurado')

    subject = f"Inscripción recibida: {nombre} - {categoria}"
    body = "<p>Se ha recibido una inscripción con los siguientes datos:</p><ul>"
    for label, value in fields.items():
        body += f"<li><strong>{label}:</strong> {value}</li>"
    body += "</ul><p>Archivos:</p><ul>"
    for link in file_links:
        body += f"<li><a href='{link}'>{link}</a></li>"
    body += "</ul>"

    msg = MIMEText(body, 'html')
    msg['Subject'] = subject
    msg['From'] = email
    msg['To'] = email

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(email, password)
        server.sendmail(email, [email], msg.as_string())
