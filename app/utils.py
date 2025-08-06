import os
import csv
import json

MENU_CONFIG = 'menu_config.csv'
FILE_CONFIG = 'file_config.csv'
FIELD_CONFIG = 'field_config.json'
SETTINGS_FILE = 'settings.json'
SUBMISSIONS_FILE = 'submissions.csv'


def init_configs():
    if not os.path.exists(MENU_CONFIG):
        with open(MENU_CONFIG, 'w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(['emisores', 'EMISORES', '', 'Inscripciones'])
    if not os.path.exists(FILE_CONFIG):
        with open(FILE_CONFIG, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['category_key', 'file_label'])
            writer.writerow(['emisores', 'Archivo 1'])
    if not os.path.exists(FIELD_CONFIG):
        default_fields = {
            "emisores": [
                {
                    "name": "nombre",
                    "label": "Nombre completo",
                    "type": "text",
                    "required": True
                },
                {
                    "name": "email",
                    "label": "Correo electrónico",
                    "type": "email",
                    "required": True
                }
            ]
        }
        with open(FIELD_CONFIG, 'w', encoding='utf-8') as f:
            json.dump(default_fields, f, ensure_ascii=False, indent=2)
    if not os.path.exists(SETTINGS_FILE):
        default_settings = {
            "mail": {
                "mail_user": "",
                "mail_password": "",
                "smtp_host": "smtp.office365.com",
                "smtp_port": 587,
                "tested": False,
            },
            "onedrive": {
                "client_id": "",
                "client_secret": "",
                "tenant_id": "",
                "user_id": "",
                "tested": False,
            },
        }
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_settings, f, ensure_ascii=False, indent=2)


def load_menu():
    items = []
    with open(MENU_CONFIG, newline='', encoding='utf-8') as f:
        for row in csv.reader(f):
            if not row:
                continue
            key = row[0]
            name = row[1] if len(row) > 1 else ''
            parent = row[2] if len(row) > 2 else ''
            base_path = row[3] if len(row) > 3 else ''
            items.append({'key': key, 'name': name, 'parent': parent, 'base_path': base_path})
    return items


def load_file_labels(cat):
    labels = []
    if not os.path.exists(FILE_CONFIG):
        return labels
    with open(FILE_CONFIG, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r['category_key'] == cat:
                labels.append(r['file_label'])
    return labels


def load_text_fields(cat):
    if not os.path.exists(FIELD_CONFIG):
        return []
    with open(FIELD_CONFIG, encoding='utf-8') as f:
        data = json.load(f)
    return data.get(cat, [])


def save_text_fields(cat: str, fields: list) -> None:
    """Persist text field configuration for a category.

    Parameters
    ----------
    cat: str
        Identifier of the category whose fields are being saved.
    fields: list
        List of dictionaries representing field metadata.
    """
    data = {}
    if os.path.exists(FIELD_CONFIG):
        with open(FIELD_CONFIG, encoding='utf-8') as f:
            data = json.load(f)
    data[cat] = fields
    with open(FIELD_CONFIG, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_submission(cat: str, fields: dict, files: list) -> None:
    """Append a user submission to the submissions file."""
    exists = os.path.exists(SUBMISSIONS_FILE)
    with open(SUBMISSIONS_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not exists:
            writer.writerow(['category', 'fields', 'files'])
        writer.writerow([
            cat,
            json.dumps(fields, ensure_ascii=False),
            json.dumps(files, ensure_ascii=False),
        ])


def load_submissions(cat: str = '') -> list:
    """Return stored submissions, optionally filtered by category."""
    if not os.path.exists(SUBMISSIONS_FILE):
        return []
    submissions = []
    with open(SUBMISSIONS_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if cat and row['category'] != cat:
                continue
            submissions.append(
                {
                    'category': row['category'],
                    'fields': json.loads(row['fields']),
                    'files': json.loads(row['files']),
                }
            )
    return submissions


def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        init_configs()
    with open(SETTINGS_FILE, encoding='utf-8') as f:
        data = json.load(f)
    defaults = {
        "mail": {
            "mail_user": "",
            "mail_password": "",
            "smtp_host": "smtp.office365.com",
            "smtp_port": 587,
            "tested": False,
        },
        "onedrive": {
            "client_id": "",
            "client_secret": "",
            "tenant_id": "",
            "user_id": "",
            "tested": False,
        },
    }
    for section, values in defaults.items():
        data.setdefault(section, {})
        for k, v in values.items():
            data[section].setdefault(k, v)
    return data


def save_settings(data):
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_setup_complete():
    settings = load_settings()
    mail = settings.get('mail', {})
    drive = settings.get('onedrive', {})
    mail_ok = mail.get('tested')
    drive_ok = all(drive.get(k) for k in ('client_id', 'client_secret', 'tenant_id', 'user_id')) and drive.get('tested')
    menu_ok = bool(load_menu())
    return mail_ok and drive_ok and menu_ok
