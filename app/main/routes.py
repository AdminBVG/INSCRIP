import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename

from ..utils import (
    load_menu,
    load_file_fields,
    load_text_fields,
    is_setup_complete,
    save_submission,
    load_settings,
)
from services.onedrive import upload_files
from services.mail import send_mail
from services.graph_auth import GraphAPIError, get_access_token

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    setup_ok = is_setup_complete()
    current_app.logger.info("is_setup_complete: %s", setup_ok)
    if not setup_ok:
        flash('Debe completar la configuración antes de continuar', 'error')
        return redirect(url_for('admin.settings'))
    menu = load_menu()
    roots = [i for i in menu if i['parent'] == '']
    return render_template('index.html', menu=roots, title='Inscripciones')


@main_bp.route('/inscripcion/<key>', methods=['GET', 'POST'])
def inscripcion(key):
    setup_ok = is_setup_complete()
    current_app.logger.info("is_setup_complete: %s", setup_ok)
    if not setup_ok:
        flash('Debe completar la configuración antes de continuar', 'error')
        return redirect(url_for('admin.settings'))
    menu = load_menu()
    cat = next((i for i in menu if i['key'] == key), None)
    if not cat:
        flash('Categoría no encontrada', 'error')
        return redirect(url_for('main.index'))

    children = [i for i in menu if i['parent'] == key]
    if children and request.method == 'GET':
        return render_template('index.html', menu=children, title=cat['name'])

    files_cfg = load_file_fields(key)
    fields = load_text_fields(key)

    if request.method == 'POST':
        current_app.logger.info("Inicio de inscripción: %s", key)
        current_app.logger.info("Datos de formulario: %s", dict(request.form))
        current_app.logger.info(
            "Archivos recibidos: %s",
            {k: v.filename for k, v in request.files.items()},
        )
        form_values = {}
        nombre = ''
        for field in fields:
            value = request.form.get(field['name'], '').strip()
            if field.get('required') and not value:
                flash(f"El campo {field['label']} es obligatorio", 'error')
                return redirect(request.url)
            form_values[field['label']] = value
            if field['name'] == 'nombre':
                nombre = value
        if not nombre:
            flash('Debe incluir el campo nombre', 'error')
            return redirect(request.url)

        uploaded_files = []
        file_info = []
        allowed_exts = [e.lower() for e in current_app.config['UPLOAD_EXTENSIONS']]
        for fcfg in files_cfg:
            f = request.files.get(fcfg['name'])
            if fcfg.get('required') and (not f or f.filename == ''):
                flash(f"El archivo {fcfg['label']} es obligatorio", 'error')
                return redirect(request.url)
            if f and f.filename != '':
                filename = secure_filename(f.filename)
                ext = os.path.splitext(filename)[1].lower()
                if ext not in allowed_exts:
                    flash(f'Archivo no permitido: {filename}', 'error')
                    return redirect(request.url)
                f.stream.seek(0, os.SEEK_END)
                size = f.stream.tell()
                f.stream.seek(0)
                file_info.append({"name": filename, "size": size})
                uploaded_files.append(f)

        current_app.logger.info("Archivos listos para subir: %s", file_info)
        if not uploaded_files:
            flash('Debe subir al menos un archivo', 'error')
            return redirect(request.url)

        cfg = load_settings()
        mail_cfg = cfg.get('mail', {})
        drive_cfg = cfg.get('onedrive', {})
        base_path = (cat.get('base_path') or drive_cfg.get('base_path', '')).strip('/')
        recipients_cfg = cat.get('notify_emails', '').strip()

        missing = []
        if not mail_cfg.get('tested'):
            missing.append('correo')
        if not all(drive_cfg.get(k) for k in ('client_id', 'client_secret', 'tenant_id', 'user_id')):
            missing.append('credenciales de OneDrive')
        if not base_path:
            missing.append('ruta base de OneDrive')
        if not recipients_cfg:
            missing.append('destinatarios')
        if missing:
            msg = ", ".join(missing)
            current_app.logger.error("Configuración incompleta: falta %s", msg)
            flash(f"Configuración incompleta: falta {msg}", 'error')
            return redirect(request.url)

        dest_dir = "/".join([base_path, key.strip("/"), nombre]).replace("//", "/")
        if ':' in dest_dir or '\\' in dest_dir:
            current_app.logger.error("Ruta de OneDrive no válida: %s", dest_dir)
            flash(f"Ruta de OneDrive no válida: {dest_dir}", 'error')
            return redirect(request.url)
        current_app.logger.info("Ruta de OneDrive final: %s", dest_dir)

        to_recipients = [r.strip() for r in recipients_cfg.split(',') if r.strip()]
        if not to_recipients:
            flash('No hay destinatarios configurados para esta categoría', 'error')
            return redirect(request.url)
        current_app.logger.info("Destinatarios: %s", to_recipients)

        try:
            token = get_access_token(drive_cfg)
            current_app.logger.info("Token de Graph obtenido: %s", bool(token))
        except GraphAPIError as e:
            current_app.logger.exception("Error obteniendo token de Graph")
            flash(f"Error obteniendo token de Graph: {e}", 'error')
            return redirect(url_for('main.index'))

        test_mode = request.args.get('ab')
        current_app.logger.info("Modo A/B: %s", test_mode)

        file_links = []
        if test_mode != 'B':
            try:
                folder_path, file_links = upload_files(
                    token, drive_cfg['user_id'], base_path, key, nombre, uploaded_files
                )
                current_app.logger.info("Archivos subidos a: %s", folder_path)
                save_submission(key, form_values, file_links)
            except GraphAPIError as e:
                current_app.logger.exception("Error al subir archivos a OneDrive")
                flash(f"Error subiendo archivo a OneDrive: {e}", 'error')
                return redirect(url_for('main.index'))
        else:
            current_app.logger.info("Modo B: se omite la subida de archivos")
            save_submission(key, form_values, file_links)

        if test_mode != 'A':
            try:
                send_mail(
                    token,
                    drive_cfg['user_id'],
                    nombre,
                    cat['name'],
                    form_values,
                    file_links,
                    to_recipients,
                )
                flash('Inscripción completada: correo enviado', 'success')
            except GraphAPIError as e:
                current_app.logger.exception("Error enviando correo")
                if test_mode == 'B':
                    flash(f"Error enviando correo: {e}", 'error')
                else:
                    flash(f"Archivos subidos pero falló el envío de correo: {e}", 'error')
        else:
            flash('Archivos subidos sin enviar correo (modo A)', 'info')

        return redirect(url_for('main.index'))

    return render_template('form.html', category_name=cat['name'], files=files_cfg, fields=fields)
