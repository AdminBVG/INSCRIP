from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash

from ..db import SessionLocal
from ..models import Category
from ..utils import (
    load_menu,
    load_settings,
    save_settings,
    load_text_fields,
    save_text_fields,
    load_file_fields,
    save_file_fields,
    load_submissions,
)

admin_bp = Blueprint('admin', __name__)


def _validate_microsoft_email(email: str) -> bool:
    forbidden = {'gmail.com', 'yahoo.com', 'icloud.com', 'gmx.com', 'protonmail.com'}
    domain = email.split('@')[-1].lower()
    microsoft_domains = {'outlook.com', 'office365.com', 'hotmail.com', 'live.com'}
    return domain in microsoft_domains or domain not in forbidden


def _build_tree(items):
    nodes = {i['key']: {**i, 'children': []} for i in items}
    roots = []
    for item in nodes.values():
        parent = item['parent']
        if parent and parent in nodes:
            nodes[parent]['children'].append(item)
        else:
            roots.append(item)
    return roots

@admin_bp.route('/menu', methods=['GET', 'POST'])
def menu():
    menu = load_menu(include_inactive=True)
    if request.method == 'POST':
        key = request.form['key'].strip()
        name = request.form['name'].strip()
        parent_id = request.form.get('parent_id', type=int)
        base_path = request.form.get('base_path', '').strip()
        active = bool(request.form.get('active'))
        with SessionLocal() as db:
            parent = db.query(Category).filter_by(id=parent_id).first() if parent_id else None
            db.add(
                Category(
                    key=key,
                    name=name,
                    parent=parent,
                    base_path=base_path,
                    active=active,
                )
            )
            db.commit()
        flash('Categoría creada')
        return redirect(url_for('admin.menu'))
    tree = _build_tree(menu)
    return render_template('admin_menu.html', menu=tree)


@admin_bp.route('/menu/<int:cat_id>/edit', methods=['GET', 'POST'])
def edit_category(cat_id: int):
    with SessionLocal() as db:
        category = db.query(Category).filter_by(id=cat_id).first()
        if not category:
            flash('Categoría no encontrada')
            return redirect(url_for('admin.menu'))
        if request.method == 'POST':
            category.key = request.form['key'].strip()
            category.name = request.form['name'].strip()
            parent_id = request.form.get('parent_id', type=int)
            category.parent = (
                db.query(Category).filter_by(id=parent_id).first() if parent_id else None
            )
            category.base_path = request.form.get('base_path', '').strip()
            category.active = bool(request.form.get('active'))
            db.commit()
            flash('Categoría actualizada')
            return redirect(url_for('admin.menu'))
        categories = [c for c in load_menu(include_inactive=True) if c['id'] != cat_id]
        tree = _build_tree(categories)
        return render_template(
            'admin_category_edit.html', category=category, menu=tree
        )


@admin_bp.route('/menu/<int:cat_id>/delete', methods=['POST'])
def delete_category(cat_id: int):
    with SessionLocal() as db:
        category = db.query(Category).filter_by(id=cat_id).first()
        if category:
            category.active = False
            db.commit()
            flash('Categoría desactivada')
        else:
            flash('Categoría no encontrada')
    return redirect(url_for('admin.menu'))

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
            password = request.form.get('mail_password', '')
            if not email or not _validate_microsoft_email(email):
                flash('El correo debe ser una cuenta de Microsoft')
                return redirect(url_for('admin.settings'))
            try:
                from services.mail import test_connection as mail_test

                mail_test(email, password)
            except Exception as e:
                flash(f'Error al verificar correo: {e}')
                return redirect(url_for('admin.settings'))
            cfg['mail']['mail_user'] = email
            cfg['mail']['mail_password'] = password
            cfg['mail']['smtp_host'] = 'smtp.office365.com'
            cfg['mail']['smtp_port'] = 587
            cfg['mail']['tested'] = True
            cfg['mail']['updated_at'] = datetime.now().isoformat()
            cfg['mail']['tested_at'] = datetime.now().isoformat()
            save_settings(cfg)
            flash('Credenciales de correo guardadas y verificadas')
        elif action == 'save_onedrive':
            email = request.form.get('user_id', '')
            if not email or not _validate_microsoft_email(email):
                flash('El correo debe ser una cuenta de Microsoft')
                return redirect(url_for('admin.settings'))
            client_id = request.form.get('client_id', '')
            client_secret = request.form.get('client_secret', '')
            tenant_id = request.form.get('tenant_id', '')
            try:
                from services.onedrive import test_connection as drive_test

                drive_test(client_id, tenant_id, client_secret)
            except Exception as e:
                flash(f'Error al verificar OneDrive: {e}')
                return redirect(url_for('admin.settings'))
            cfg['onedrive']['client_id'] = client_id
            cfg['onedrive']['client_secret'] = client_secret
            cfg['onedrive']['tenant_id'] = tenant_id
            cfg['onedrive']['user_id'] = email
            cfg['onedrive']['tested'] = True
            cfg['onedrive']['updated_at'] = datetime.now().isoformat()
            cfg['onedrive']['tested_at'] = datetime.now().isoformat()
            save_settings(cfg)
            flash('Credenciales de OneDrive guardadas y verificadas')
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
