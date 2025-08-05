# services/mail.py
import requests, os

CLIENT_ID = os.getenv('CLIENT_ID')
TENANT_ID = os.getenv('TENANT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
USER_ID = os.getenv('USER_ID')
RECIPIENT = os.getenv('RECIPIENT_EMAIL', USER_ID)

def get_access_token():
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        'client_id': CLIENT_ID,
        'scope': 'https://graph.microsoft.com/.default',
        'client_secret': CLIENT_SECRET,
        'grant_type': 'client_credentials'
    }
    response = requests.post(url, data=data)
    return response.json()['access_token']

def send_mail(nombre, categoria, file_links):
    token = get_access_token()
    subject = f"Inscripción recibida: {nombre} - {categoria}"
    body = f"<p>Se ha recibido una inscripción:</p><ul>"
    for link in file_links:
        body += f"<li><a href='{link}'>{link}</a></li>"
    body += "</ul>"

    message = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "HTML",
                "content": body
            },
            "toRecipients": [
                {"emailAddress": {"address": RECIPIENT}}
            ]
        }
    }

    url = f"https://graph.microsoft.com/v1.0/users/{USER_ID}/sendMail"
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    r = requests.post(url, headers=headers, json=message)
    if r.status_code >= 300:
        raise Exception(f"Error enviando correo: {r.text}")
