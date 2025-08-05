# services/onedrive.py
import requests, os
from werkzeug.utils import secure_filename

CLIENT_ID = os.getenv('CLIENT_ID')
TENANT_ID = os.getenv('TENANT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
USER_ID = os.getenv('USER_ID')
CARPETA_BASE = os.getenv('CARPETA_BASE', 'Inscripciones')

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

def create_folder_if_not_exists(token, folder_name, parent='root'):
    url = f'https://graph.microsoft.com/v1.0/users/{USER_ID}/drive/{parent}/children'
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    data = {
        "name": folder_name,
        "folder": {},
        "@microsoft.graph.conflictBehavior": "rename"
    }
    r = requests.post(url, headers=headers, json=data)
    return r.json()['id']

def upload_files(nombre, categoria, files):
    token = get_access_token()
    root_id = create_folder_if_not_exists(token, CARPETA_BASE)
    cat_id = create_folder_if_not_exists(token, categoria, f'items/{root_id}')
    user_id = create_folder_if_not_exists(token, nombre, f'items/{cat_id}')
    
    file_links = []
    for f in files:
        filename = secure_filename(f.filename)
        content = f.read()
        upload_url = f'https://graph.microsoft.com/v1.0/users/{USER_ID}/drive/items/{user_id}:/{filename}:/content'
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/octet-stream'}
        r = requests.put(upload_url, headers=headers, data=content)
        file_links.append(r.json()['webUrl'])

    return f"{CARPETA_BASE}/{categoria}/{nombre}", file_links
