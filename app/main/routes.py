import os
import logging
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


logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    setup_ok = is_setup_complete()
    logger.info("is_setup_complete: %s", setup_ok)
    if not setup_ok:
        flash('Debe completar la configuración antes de continuar', 'error')
        return redirect(url_for('admin.settings'))
    menu = load_menu()
    roots = [i for i in menu if i['parent'] == '']
    return render_template('index.html', menu=roots, title='Inscripciones')


@main_bp.route('/inscripcion/<key>', methods=['GET', 'POST'])
def inscripcion(key):
    setup_ok = is_setup_complete()
    logger.info("is_setup_complete: %s", setup_ok)
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
        logger.info("Inicio de inscripción: %s", key)
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
        allowed_exts = current_app.config['UPLOAD_EXTENSIONS']
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
                uploaded_files.append(f)

        if not uploaded_files:
            flash('Debe subir al menos un archivo', 'error')
            return redirect(request.url)

        cfg = load_settings()
        mail_cfg = cfg.get('mail', {})
        drive_cfg = cfg.get('onedrive', {})
        base_path = cat.get('base_path') or drive_cfg.get('base_path')
        recipients_cfg = cat.get('notify_emails', '').strip()
        if not (
            mail_cfg.get('tested')
            and all(
                drive_cfg.get(k)
                for k in ('client_id', 'client_secret', 'tenant_id', 'user_id')
            )
            and base_path
            and recipients_cfg
        ):
            flash('Configuración incompleta para esta categoría', 'error')
            return redirect(request.url)

        to_recipients = [r.strip() for r in recipients_cfg.split(',') if r.strip()]
        if not to_recipients:
            flash('No hay destinatarios configurados para esta categoría', 'error')
            return redirect(request.url)

        try:
            token = get_access_token(drive_cfg)
        except GraphAPIError as e:
            logger.exception("Error obteniendo token de Graph")
            flash(f"Error obteniendo token de Graph: {e}", 'error')
            return redirect(url_for('main.index'))

        try:
            folder_path, file_links = upload_files(
                token, drive_cfg['user_id'], base_path, key, nombre, uploaded_files
            )
            save_submission(key, form_values, file_links)
        except GraphAPIError as e:
            logger.exception("Error al subir archivos a OneDrive")
            flash(f"Error subiendo archivo a OneDrive: {e}", 'error')
            return redirect(url_for('main.index'))

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
            flash('Inscripción completada: archivos subidos y correo enviado', 'success')
        except GraphAPIError as e:
            logger.exception("Error enviando correo")
            flash(f"Archivos subidos pero falló el envío de correo: {e}", 'error')

        return redirect(url_for('main.index'))

    return render_template('form.html', category_name=cat['name'], files=files_cfg, fields=fields)
