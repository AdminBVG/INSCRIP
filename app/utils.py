import os
import csv
import json

MENU_CONFIG = 'menu_config.csv'
FILE_CONFIG = 'file_config.csv'
FIELD_CONFIG = 'field_config.json'


def init_configs():
    if not os.path.exists(MENU_CONFIG):
        with open(MENU_CONFIG, 'w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(['emisores', 'EMISORES', ''])
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


def load_menu():
    items = []
    with open(MENU_CONFIG, newline='', encoding='utf-8') as f:
        for key, name, parent in csv.reader(f):
            items.append({'key': key, 'name': name, 'parent': parent})
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
