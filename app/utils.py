import os
import csv
import json

MENU_CONFIG = 'menu_config.csv'
FILE_CONFIG = 'file_config.csv'
FIELD_CONFIG = 'field_config.json'
SETTINGS_FILE = 'settings.json'


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
            "mail": {"tested": False},
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


def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        init_configs()
    with open(SETTINGS_FILE, encoding='utf-8') as f:
        return json.load(f)


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
