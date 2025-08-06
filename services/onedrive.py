import requests
from werkzeug.utils import secure_filename
from app.utils import load_settings
from .graph_auth import get_access_token, GraphAPIError


def test_connection(client_id, tenant_id, client_secret):
    get_access_token({'client_id': client_id, 'tenant_id': tenant_id, 'client_secret': client_secret})


def create_folder_if_not_exists(token, user_id, folder_name, parent='root'):
    headers = {'Authorization': f'Bearer {token}'}
    base_url = f"https://graph.microsoft.com/v1.0/users/{user_id}/drive/{parent}/children"
    search_url = base_url + f"?$filter=name eq '{folder_name}'"
    r = requests.get(search_url, headers=headers)
    if r.status_code >= 400:
        raise GraphAPIError(r.status_code, r.text)
    items = r.json().get('value', [])
    if items:
        return items[0]['id']
    headers['Content-Type'] = 'application/json'
    data = {'name': folder_name, 'folder': {}, '@microsoft.graph.conflictBehavior': 'rename'}
    r = requests.post(base_url, headers=headers, json=data)
    if r.status_code >= 400:
        raise GraphAPIError(r.status_code, r.text)
    return r.json()['id']


def upload_files(nombre, categoria, base_path, files):
    cfg = load_settings()['onedrive']
    user_id = cfg.get('user_id')
    token = get_access_token(cfg)
    root_id = create_folder_if_not_exists(token, user_id, base_path)
    cat_id = create_folder_if_not_exists(token, user_id, categoria, f"items/{root_id}")
    user_folder = create_folder_if_not_exists(token, user_id, nombre, f"items/{cat_id}")
    file_links = []
    for f in files:
        filename = secure_filename(f.filename)
        content = f.read()
        upload_url = f"https://graph.microsoft.com/v1.0/users/{user_id}/drive/items/{user_folder}:/{filename}:/content"
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/octet-stream'}
        r = requests.put(upload_url, headers=headers, data=content)
        if r.status_code >= 400:
            raise GraphAPIError(r.status_code, r.text)
        file_links.append(r.json()['webUrl'])
    return f"{base_path}/{categoria}/{nombre}", file_links
