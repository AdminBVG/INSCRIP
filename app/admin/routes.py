import csv
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash

from ..utils import (
    load_menu,
    load_settings,
    save_settings,
    load_text_fields,
    save_text_fields,
    load_file_fields,
    save_file_fields,
    load_submissions,
    MENU_CONFIG,
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
    cat = request.values.get('category', '')
    files_data = load_file_fields(cat) if cat else []
    if request.method == 'POST':
        action = request.form.get('action')
        index = request.form.get('index', type=int)
        if action in {'add', 'update'}:
            name = request.form.get('name', '').strip()
            label = request.form.get('label', '').strip()
            description = request.form.get('description', '').strip()
            required = bool(request.form.get('required'))
            if not name or not label:
                flash('Nombre e identificador son obligatorios')
                return redirect(url_for('admin.files', category=cat))
            file_cfg = {
                'name': name,
                'label': label,
                'description': description,
                'required': required,
            }
            if action == 'add':
                files_data.append(file_cfg)
            else:
                if index is not None and 0 <= index < len(files_data):
                    files_data[index] = file_cfg
        elif action == 'delete' and index is not None:
            if 0 <= index < len(files_data):
                files_data.pop(index)
        elif action == 'up' and index is not None:
            if index > 0:
                files_data[index - 1], files_data[index] = files_data[index], files_data[index - 1]
        elif action == 'down' and index is not None:
            if index < len(files_data) - 1:
                files_data[index + 1], files_data[index] = files_data[index], files_data[index + 1]
        save_file_fields(cat, files_data)
        flash('Archivos actualizados')
        return redirect(url_for('admin.files', category=cat))
    return render_template('admin_files.html', menu=menu, files=files_data, selected_cat=cat)


@admin_bp.route('/fields', methods=['GET', 'POST'])
def fields():
    menu = load_menu()
    cat = request.values.get('category', '')
    fields_data = load_text_fields(cat) if cat else []
    if request.method == 'POST':
        action = request.form.get('action')
        index = request.form.get('index', type=int)
        if action in {'add', 'update'}:
            name = request.form.get('name', '').strip()
            label = request.form.get('label', '').strip()
            ftype = request.form.get('type', 'text').strip() or 'text'
            required = bool(request.form.get('required'))
            if not name or not label:
                flash('Nombre y etiqueta son obligatorios')
                return redirect(url_for('admin.fields', category=cat))
            field = {'name': name, 'label': label, 'type': ftype, 'required': required}
            if action == 'add':
                fields_data.append(field)
            else:
                if index is not None and 0 <= index < len(fields_data):
                    fields_data[index] = field
        elif action == 'delete' and index is not None:
            if 0 <= index < len(fields_data):
                fields_data.pop(index)
        elif action == 'up' and index is not None:
            if index > 0:
                fields_data[index - 1], fields_data[index] = fields_data[index], fields_data[index - 1]
        elif action == 'down' and index is not None:
            if index < len(fields_data) - 1:
                fields_data[index + 1], fields_data[index] = fields_data[index], fields_data[index + 1]
        save_text_fields(cat, fields_data)
        flash('Campos actualizados')
        return redirect(url_for('admin.fields', category=cat))
    return render_template('admin_fields.html', menu=menu, fields=fields_data, selected_cat=cat)


@admin_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    cfg = load_settings()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'test_mail':
            try:
                email = cfg['mail'].get('mail_user', '')
                password = cfg['mail'].get('mail_password', '')
                if not email or not password:
                    raise ValueError('Correo no configurado')
                if not _validate_microsoft_email(email):
                    raise ValueError('El correo debe ser una cuenta de Microsoft')
                from services.mail import test_connection as mail_test

                mail_test()
                cfg['mail']['tested'] = True
                cfg['mail']['tested_at'] = datetime.now().isoformat()
                save_settings(cfg)
                flash('Correo verificado')
            except Exception as e:
                cfg['mail']['tested'] = False
                save_settings(cfg)
                flash(f'Error: {e}')
        elif action == 'save_mail':
            email = request.form.get('mail_user', '')
            if not email or not _validate_microsoft_email(email):
                flash('El correo debe ser una cuenta de Microsoft')
                return redirect(url_for('admin.settings'))
            cfg['mail']['mail_user'] = email
            cfg['mail']['mail_password'] = request.form.get('mail_password', '')
            cfg['mail']['smtp_host'] = 'smtp.office365.com'
            cfg['mail']['smtp_port'] = 587
            cfg['mail']['tested'] = False
            cfg['mail']['updated_at'] = datetime.now().isoformat()
            cfg['mail']['tested_at'] = ''
            save_settings(cfg)
            flash('Credenciales de correo guardadas')
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
            cfg['onedrive']['updated_at'] = datetime.now().isoformat()
            cfg['onedrive']['tested_at'] = ''
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
                cfg['onedrive']['tested_at'] = datetime.now().isoformat()
                save_settings(cfg)
                flash('Conexión OneDrive verificada')
            except Exception as e:
                cfg['onedrive']['tested'] = False
                save_settings(cfg)
                flash(f'Error: {e}')
        return redirect(url_for('admin.settings'))
    return render_template('admin_settings.html', settings=cfg)


@admin_bp.route('/submissions')
def submissions():
    menu = load_menu()
    cat = request.args.get('category', '')
    data = load_submissions(cat)
    menu_map = {m['key']: m['name'] for m in menu}
    for item in data:
        item['category_name'] = menu_map.get(item['category'], item['category'])
    return render_template(
        'admin_submissions.html',
        menu=menu,
        submissions=data,
        selected_cat=cat,
    )
