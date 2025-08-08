import logging
import requests
from werkzeug.utils import secure_filename
from app.utils import load_settings
from .graph_auth import get_access_token, GraphAPIError

logger = logging.getLogger(__name__)


def test_connection(client_id, tenant_id, client_secret):
    get_access_token({'client_id': client_id, 'tenant_id': tenant_id, 'client_secret': client_secret})


def create_folder_if_not_exists(token, user_id, folder_name, parent='root'):
    headers = {'Authorization': f'Bearer {token}'}
    base_url = f"https://graph.microsoft.com/v1.0/users/{user_id}/drive/{parent}/children"
    try:
        r = requests.get(
            base_url,
            headers=headers,
            params={"$filter": f"name eq '{folder_name}'"},
        )
    except requests.RequestException as e:
        logger.exception("Error consultando carpeta en OneDrive")
        raise GraphAPIError(0, str(e)) from e
    if r.status_code >= 400:
        raise GraphAPIError(r.status_code, r.text)
    items = r.json().get("value", [])
    if items:
        return items[0]["id"]
    headers["Content-Type"] = "application/json"
    data = {
        "name": folder_name,
        "folder": {},
        "@microsoft.graph.conflictBehavior": "rename",
    }
    try:
        r = requests.post(base_url, headers=headers, json=data)
    except requests.RequestException as e:
        logger.exception("Error creando carpeta en OneDrive")
        raise GraphAPIError(0, str(e)) from e
    if r.status_code >= 400:
        raise GraphAPIError(r.status_code, r.text)
    return r.json()["id"]


def upload_files(nombre, categoria, base_path, files):
    print('upload_files() llamado')
    cfg = load_settings().get('onedrive', {})
    client_id = cfg.get('client_id')
    client_secret = cfg.get('client_secret')
    tenant_id = cfg.get('tenant_id')
    user_id = cfg.get('user_id')
    if not all([client_id, client_secret, tenant_id, user_id]):
        raise ValueError('Credenciales de OneDrive incompletas')
    token = get_access_token(cfg)
    parent_id = "root"
    for part in base_path.strip("/").split("/"):
        parent_ref = f"items/{parent_id}" if parent_id != "root" else parent_id
        parent_id = create_folder_if_not_exists(token, user_id, part, parent_ref)
    root_id = parent_id
    cat_id = create_folder_if_not_exists(
        token, user_id, categoria, f"items/{root_id}"
    )
    user_folder = create_folder_if_not_exists(
        token, user_id, nombre, f"items/{cat_id}"
    )
    file_links = []
    for f in files:
        filename = secure_filename(f.filename)
        f.stream.seek(0)
        content = f.read()
        upload_url = f"https://graph.microsoft.com/v1.0/users/{user_id}/drive/items/{user_folder}:/{filename}:/content"
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/octet-stream'}
        try:
            r = requests.put(upload_url, headers=headers, data=content)
        except requests.RequestException as e:
            logger.exception("Error subiendo archivo a OneDrive")
            raise GraphAPIError(0, str(e)) from e
        if r.status_code >= 400:
            raise GraphAPIError(r.status_code, r.text)
        file_links.append(r.json()['webUrl'])
    print('upload_files() completado')
    return f"{base_path}/{categoria}/{nombre}", file_links
