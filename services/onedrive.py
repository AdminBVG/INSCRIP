# services/onedrive.py
import os
import requests
from werkzeug.utils import secure_filename

CLIENT_ID = os.getenv("CLIENT_ID")
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
USER_ID = os.getenv("USER_ID")
CARPETA_BASE = os.getenv("CARPETA_BASE", "Inscripciones")


def get_access_token():
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        "client_id": CLIENT_ID,
        "scope": "https://graph.microsoft.com/.default",
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials",
    }
    response = requests.post(url, data=data)
    if response.status_code >= 400:
        raise Exception(f"Error obteniendo token: {response.text}")
    return response.json()["access_token"]


def create_folder_if_not_exists(token, folder_name, parent="root"):
    headers = {"Authorization": f"Bearer {token}"}
    base_url = f"https://graph.microsoft.com/v1.0/users/{USER_ID}/drive/{parent}/children"

    # Buscar si la carpeta ya existe
    search_url = base_url + f"?$filter=name eq '{folder_name}'"
    r = requests.get(search_url, headers=headers)
    if r.status_code >= 400:
        raise Exception(f"Error buscando carpeta: {r.text}")
    items = r.json().get("value", [])
    if items:
        return items[0]["id"]

    # Crear carpeta si no existe
    headers["Content-Type"] = "application/json"
    data = {"name": folder_name, "folder": {}, "@microsoft.graph.conflictBehavior": "rename"}
    r = requests.post(base_url, headers=headers, json=data)
    if r.status_code >= 400:
        raise Exception(f"Error creando carpeta: {r.text}")
    return r.json()["id"]


def upload_files(nombre, categoria, files):
    token = get_access_token()
    root_id = create_folder_if_not_exists(token, CARPETA_BASE)
    cat_id = create_folder_if_not_exists(token, categoria, f"items/{root_id}")
    user_id = create_folder_if_not_exists(token, nombre, f"items/{cat_id}")

    file_links = []
    for f in files:
        filename = secure_filename(f.filename)
        content = f.read()
        upload_url = f"https://graph.microsoft.com/v1.0/users/{USER_ID}/drive/items/{user_id}:/{filename}:/content"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/octet-stream"}
        r = requests.put(upload_url, headers=headers, data=content)
        if r.status_code >= 400:
            raise Exception(f"Error subiendo archivo {filename}: {r.text}")
        file_links.append(r.json()["webUrl"])

    return f"{CARPETA_BASE}/{categoria}/{nombre}", file_links
