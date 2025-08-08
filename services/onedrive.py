import logging
import requests
from werkzeug.utils import secure_filename
from .graph_auth import GraphAPIError

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
        r.raise_for_status()
    except requests.RequestException as e:
        logger.exception("Error consultando carpeta en OneDrive")
        status = getattr(e.response, 'status_code', 0)
        text = getattr(e.response, 'text', str(e))
        raise GraphAPIError(status, text) from e
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
        r.raise_for_status()
    except requests.RequestException as e:
        logger.exception("Error creando carpeta en OneDrive")
        status = getattr(e.response, 'status_code', 0)
        text = getattr(e.response, 'text', str(e))
        raise GraphAPIError(status, text) from e
    return r.json()["id"]


def upload_files(token, user_id, base_path, categoria, nombre, files):
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
    logger.info("Carpeta creada en OneDrive: %s/%s/%s", base_path, categoria, nombre)
    file_links = []
    for f in files:
        filename = secure_filename(f.filename)
        f.stream.seek(0)
        content = f.read()
        upload_url = f"https://graph.microsoft.com/v1.0/users/{user_id}/drive/items/{user_folder}:/{filename}:/content"
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/octet-stream'}
        try:
            r = requests.put(upload_url, headers=headers, data=content)
            r.raise_for_status()
        except requests.RequestException as e:
            logger.exception("Error subiendo archivo a OneDrive")
            status = getattr(e.response, 'status_code', 0)
            text = getattr(e.response, 'text', str(e))
            raise GraphAPIError(status, text) from e
        logger.info("Archivo subido: %s", filename)
        file_links.append(r.json()['webUrl'])
    return f"{base_path}/{categoria}/{nombre}", file_links
