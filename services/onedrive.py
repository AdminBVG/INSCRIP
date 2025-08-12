import logging
from pathlib import PurePosixPath

import requests
from werkzeug.utils import secure_filename

from .graph_auth import GraphAPIError, get_access_token

logger = logging.getLogger(__name__)


def test_connection(client_id, tenant_id, client_secret):
    get_access_token({'client_id': client_id, 'tenant_id': tenant_id, 'client_secret': client_secret})


def normalize_path(*segments: str) -> str:
    """Return a normalized POSIX path without leading/trailing slashes.

    Backslashes are converted to forward slashes and consecutive separators or
    surrounding spaces are removed. When all segments are empty an empty string
    is returned.
    """
    joined = "/".join(
        s.replace("\\", "/").strip() for s in segments if s and s.strip()
    )
    if not joined:
        return ""
    return str(PurePosixPath(joined)).strip("/")


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


def _get_folder_url(token: str, user_id: str, folder_id: str) -> str:
    """Return the web URL for the given folder id."""
    headers = {'Authorization': f'Bearer {token}'}
    url = f"https://graph.microsoft.com/v1.0/users/{user_id}/drive/items/{folder_id}"
    try:
        r = requests.get(url, headers=headers, params={'$select': 'webUrl'})
        r.raise_for_status()
    except requests.RequestException as e:
        logger.exception("Error obteniendo URL de carpeta en OneDrive")
        status = getattr(e.response, 'status_code', 0)
        text = getattr(e.response, 'text', str(e))
        raise GraphAPIError(status, text) from e
    return r.json().get('webUrl', '')


def upload_files(token, user_id, dest_path, files):
    """Upload files to the given path in OneDrive.

    The path must be normalized before being passed to this function.
    Returns the web URL of the created folder.
    """
    dest_path = normalize_path(dest_path)
    logger.info("Carpeta destino OneDrive: %s", dest_path)
    parent_id = "root"
    for part in dest_path.split("/"):
        parent_ref = f"items/{parent_id}" if parent_id != "root" else parent_id
        parent_id = create_folder_if_not_exists(token, user_id, part, parent_ref)

    folder_url = _get_folder_url(token, user_id, parent_id)

    for f in files:
        filename = secure_filename(f['name'])
        content = f['content']
        upload_url = (
            f"https://graph.microsoft.com/v1.0/users/{user_id}/drive/items/{parent_id}:/{filename}:/content"
        )
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/octet-stream',
        }
        try:
            r = requests.put(upload_url, headers=headers, data=content)
            r.raise_for_status()
        except requests.RequestException as e:
            logger.exception("Error subiendo archivo a OneDrive")
            status = getattr(e.response, 'status_code', 0)
            text = getattr(e.response, 'text', str(e))
            raise GraphAPIError(status, text) from e
        logger.info("Archivo subido: %s", filename)

    return folder_url
