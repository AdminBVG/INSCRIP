from datetime import datetime
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
)

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
from services.mail import send_test_email
from services.onedrive import upload_files, normalize_path
from services.graph_auth import get_access_token, GraphAPIError

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
        notify_emails = request.form.get('notify_emails', '').strip()
        notify_cc_emails = request.form.get('notify_cc_emails', '').strip()
        active = bool(request.form.get('active'))
        with SessionLocal() as db:
            parent = db.query(Category).filter_by(id=parent_id).first() if parent_id else None
            db.add(
                Category(
                    key=key,
                    name=name,
                    parent=parent,
                    base_path=base_path,
                    notify_emails=notify_emails,
                    notify_cc_emails=notify_cc_emails,
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
            category.notify_emails = request.form.get('notify_emails', '').strip()
            category.notify_cc_emails = request.form.get('notify_cc_emails', '').strip()
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
            email = request.form.get('mail_user', '').strip() or cfg['mail'].get('mail_user', '')
            password = request.form.get('mail_password', '').strip() or cfg['mail'].get('mail_password', '')
            host = request.form.get('smtp_host', '').strip() or cfg['mail'].get('smtp_host', 'smtp.office365.com')
            port = request.form.get('smtp_port', type=int) or cfg['mail'].get('smtp_port', 587)
            try:
                if not email or not password:
                    raise ValueError('Correo no configurado')
                if not _validate_microsoft_email(email):
                    raise ValueError('El correo debe ser una cuenta de Microsoft')
                from services.mail import test_connection as mail_test

                mail_test(email, password, host, port)
                flash('Correo verificado')
            except Exception as e:
                current_app.logger.exception("Error probando correo")
                flash(f'Error probando correo: {e}')
            cfg['mail']['mail_user'] = email
            cfg['mail']['mail_password'] = password
            cfg['mail']['smtp_host'] = host
            cfg['mail']['smtp_port'] = port
            return render_template('admin_settings.html', settings=cfg)
        elif action == 'save_mail':
            email = request.form.get('mail_user', '').strip()
            password = request.form.get('mail_password', '').strip()
            host = request.form.get('smtp_host', '').strip() or 'smtp.office365.com'
            port = request.form.get('smtp_port', type=int) or 587
            if not email or not _validate_microsoft_email(email):
                flash('El correo debe ser una cuenta de Microsoft')
                return redirect(url_for('admin.settings'))
            try:
                from services.mail import test_connection as mail_test

                mail_test(email, password, host, port)
            except Exception as e:
                current_app.logger.exception("Error al verificar correo")
                flash(f'Error al verificar correo: {e}')
                return redirect(url_for('admin.settings'))
            cfg['mail']['mail_user'] = email
            cfg['mail']['mail_password'] = password
            cfg['mail']['smtp_host'] = host
            cfg['mail']['smtp_port'] = port
            cfg['mail']['tested'] = True
            cfg['mail']['updated_at'] = datetime.now().isoformat()
            cfg['mail']['tested_at'] = datetime.now().isoformat()
            save_settings(cfg)
            flash('Credenciales de correo guardadas y verificadas')
            return redirect(url_for('admin.settings'))
        elif action == 'save_onedrive':
            email = request.form.get('user_id', '').strip()
            if not email or not _validate_microsoft_email(email):
                flash('El correo debe ser una cuenta de Microsoft')
                return redirect(url_for('admin.settings'))
            client_id = request.form.get('client_id', '').strip()
            client_secret = request.form.get('client_secret', '').strip()
            tenant_id = request.form.get('tenant_id', '').strip()
            base_path = request.form.get('base_path', '').strip() or 'Inscripciones'
            try:
                from services.onedrive import test_connection as drive_test

                drive_test(client_id, tenant_id, client_secret)
            except Exception as e:
                current_app.logger.exception("Error al verificar OneDrive")
                flash(f'Error al verificar OneDrive: {e}')
                return redirect(url_for('admin.settings'))
            cfg['onedrive']['client_id'] = client_id
            cfg['onedrive']['client_secret'] = client_secret
            cfg['onedrive']['tenant_id'] = tenant_id
            cfg['onedrive']['user_id'] = email
            cfg['onedrive']['base_path'] = base_path
            cfg['onedrive']['tested'] = True
            cfg['onedrive']['updated_at'] = datetime.now().isoformat()
            cfg['onedrive']['tested_at'] = datetime.now().isoformat()
            save_settings(cfg)
            flash('Credenciales de OneDrive guardadas y verificadas')
            return redirect(url_for('admin.settings'))
        elif action == 'test_onedrive':
            client_id = request.form.get('client_id', '').strip() or cfg['onedrive'].get('client_id', '')
            client_secret = request.form.get('client_secret', '').strip() or cfg['onedrive'].get('client_secret', '')
            tenant_id = request.form.get('tenant_id', '').strip() or cfg['onedrive'].get('tenant_id', '')
            user_id = request.form.get('user_id', '').strip() or cfg['onedrive'].get('user_id', '')
            base_path = request.form.get('base_path', '').strip() or cfg['onedrive'].get('base_path', 'Inscripciones')
            try:
                from services.onedrive import test_connection as drive_test

                drive_test(client_id, tenant_id, client_secret)
                flash('Conexión OneDrive verificada')
            except Exception as e:
                current_app.logger.exception("Error probando OneDrive")
                flash(f'Error: {e}')
            cfg['onedrive']['client_id'] = client_id
            cfg['onedrive']['client_secret'] = client_secret
            cfg['onedrive']['tenant_id'] = tenant_id
            cfg['onedrive']['user_id'] = user_id
            cfg['onedrive']['base_path'] = base_path
            return render_template('admin_settings.html', settings=cfg)
        return redirect(url_for('admin.settings'))
    return render_template('admin_settings.html', settings=cfg)


@admin_bp.route('/test/mail', methods=['GET', 'POST'])
def test_mail():
    """Form to send a test email using current configuration."""
    if request.method == 'POST':
        to = request.form.get('to', '').strip()
        subject = request.form.get('subject', '').strip() or 'Prueba de correo'
        body = request.form.get('body', '').strip() or 'Correo de prueba.'
        if not to:
            flash('Debe proporcionar un destinatario')
            return redirect(request.url)
        try:
            send_test_email(to, subject, body)
            flash('Correo enviado correctamente')
        except Exception as e:  # pragma: no cover - mostrar al usuario
            current_app.logger.exception("Error enviando correo de prueba")
            flash(f'Error enviando correo: {e}')
    return render_template('test_mail.html')


@admin_bp.route('/test/onedrive', methods=['GET', 'POST'])
def test_onedrive():
    """Upload a sample file to verify OneDrive connectivity."""
    cfg = load_settings().get('onedrive', {})
    if request.method == 'POST':
        f = request.files.get('file')
        if not f or f.filename == '':
            flash('Debe seleccionar un archivo')
            return redirect(request.url)
        try:
            token = get_access_token(cfg)
            base_path = cfg.get('base_path', 'Inscripciones')
            dest_path = normalize_path(base_path, 'Test', 'Prueba')
            upload_files(token, cfg['user_id'], dest_path, [f])
            flash('Archivo de prueba subido correctamente')
        except GraphAPIError as e:
            current_app.logger.exception("Error subiendo archivo de prueba a OneDrive")
            flash(f'Error subiendo archivo a OneDrive: {e}')
        except Exception as e:  # pragma: no cover - mostrar al usuario
            current_app.logger.exception("Error en prueba de OneDrive")
            flash(f'Error: {e}')
    return render_template('test_onedrive.html')


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
