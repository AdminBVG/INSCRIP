import os
import csv
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash

from ..utils import (
    load_menu,
    load_settings,
    save_settings,
    FILE_CONFIG,
    MENU_CONFIG,
    FIELD_CONFIG,
)

admin_bp = Blueprint('admin', __name__)


def _validate_microsoft_email(email: str) -> bool:
    forbidden = {'gmail.com', 'yahoo.com', 'icloud.com', 'gmx.com', 'protonmail.com'}
    domain = email.split('@')[-1].lower()
    microsoft_domains = {'outlook.com', 'office365.com', 'hotmail.com', 'live.com'}
    return domain in microsoft_domains or domain not in forbidden

@admin_bp.route('/menu', methods=['GET', 'POST'])
def menu():
    menu = load_menu()
    if request.method == 'POST':
        key = request.form['key']
        name = request.form['name']
        parent = request.form['parent']
        base_path = request.form.get('base_path', '')
        with open(MENU_CONFIG, 'a', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow([key, name, parent, base_path])
        flash('Menú actualizado')
        return redirect(url_for('admin.menu'))
    return render_template('admin_menu.html', menu=menu)

@admin_bp.route('/files', methods=['GET', 'POST'])
def files():
    menu = load_menu()
    labels = []
    if request.method == 'POST':
        cat = request.form['category']
        labels = request.form['labels'].split(',')
        rows = []
        if os.path.exists(FILE_CONFIG):
            with open(FILE_CONFIG, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for r in reader:
                    if r['category_key'] != cat:
                        rows.append([r['category_key'], r['file_label']])
        for lbl in labels:
            rows.append([cat, lbl.strip()])
        with open(FILE_CONFIG, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['category_key', 'file_label'])
            writer.writerows(rows)
        flash('Archivos actualizados')
        return redirect(url_for('admin.files'))
    return render_template('admin_files.html', menu=menu, labels=labels)


@admin_bp.route('/fields', methods=['GET', 'POST'])
def fields():
    menu = load_menu()
    fields_data = []
    if request.method == 'POST':
        cat = request.form['category']
        try:
            fields_data = json.loads(request.form['fields'] or '[]')
        except json.JSONDecodeError:
            flash('Formato de campos inválido')
            return redirect(request.url)
        data = {}
        if os.path.exists(FIELD_CONFIG):
            with open(FIELD_CONFIG, encoding='utf-8') as f:
                data = json.load(f)
        data[cat] = fields_data
        with open(FIELD_CONFIG, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        flash('Campos actualizados')
        return redirect(url_for('admin.fields'))
    return render_template('admin_fields.html', menu=menu, fields=fields_data)


@admin_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    cfg = load_settings()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'test_mail':
            try:
                email = cfg['onedrive'].get('user_id', '')
                if not email or not _validate_microsoft_email(email):
                    raise ValueError('El correo debe ser una cuenta de Microsoft')
                from services.mail import test_connection as mail_test

                mail_test()
                cfg['mail']['tested'] = True
                save_settings(cfg)
                flash('Correo verificado')
            except Exception as e:
                flash(f'Error: {e}')
        elif action == 'save_onedrive':
            email = request.form.get('user_id', '')
            if not email or not _validate_microsoft_email(email):
                flash('El correo debe ser una cuenta de Microsoft')
                return redirect(url_for('admin.settings'))
            cfg['onedrive']['client_id'] = request.form.get('client_id', '')
            cfg['onedrive']['client_secret'] = request.form.get('client_secret', '')
            cfg['onedrive']['tenant_id'] = request.form.get('tenant_id', '')
            cfg['onedrive']['user_id'] = email
            cfg['onedrive']['tested'] = False
            save_settings(cfg)
            flash('Credenciales de OneDrive guardadas')
        elif action == 'test_onedrive':
            try:
                from services.onedrive import test_connection as drive_test

                drive_test(
                    cfg['onedrive']['client_id'],
                    cfg['onedrive']['tenant_id'],
                    cfg['onedrive']['client_secret'],
                )
                cfg['onedrive']['tested'] = True
                save_settings(cfg)
                flash('Conexión OneDrive verificada')
            except Exception as e:
                flash(f'Error: {e}')
        return redirect(url_for('admin.settings'))
    return render_template('admin_settings.html', settings=cfg)
