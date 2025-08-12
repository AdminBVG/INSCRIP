import os
import uuid
import re
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename

from ..utils import (
    load_menu,
    load_file_fields,
    load_text_fields,
    is_setup_complete,
    load_settings,
    save_log_entry,
)
from services.onedrive import upload_files, normalize_path
from services.mail import send_mail_custom
from services.graph_auth import GraphAPIError, get_access_token
from services.template_renderer import normalize_var, render_text

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
        dynamic_vars = {}
        nombre = ''
        solicitante_email = ''
        for field in fields:
            value = request.form.get(field['name'], '').strip()
            if field.get('required') and not value:
                flash(f"El campo {field['label']} es obligatorio", 'error')
                return redirect(request.url)
            form_values[field['label']] = value
            dynamic_vars[normalize_var(field['name'])] = value
            if field['name'] == 'nombre':
                nombre = value
            if field['name'] == 'email':
                solicitante_email = value
        if not nombre:
            flash('Debe incluir el campo nombre', 'error')
            return redirect(request.url)

        uploaded_files = []
        file_info = []
        file_records = []
        used_names = set()
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
                content = f.read()
                size = len(content)
                pattern = cat.get('file_pattern', '')
                storage_name = fcfg.get('storage_name', '').strip()
                final_name = filename
                if pattern:
                    now = datetime.utcnow()
                    final_name = pattern
                    label_value = storage_name or fcfg['label']
                    final_name = final_name.replace('{categoria}', cat['key'])
                    final_name = final_name.replace('{nombre}', nombre)
                    final_name = final_name.replace('{label}', label_value)
                    final_name = re.sub(
                        r'{fecha(?::([^}]+))?}',
                        lambda m: now.strftime(m.group(1) or '%Y%m%d'),
                        final_name,
                    )
                    final_name = final_name.replace('{uuid}', uuid.uuid4().hex[:8])
                    final_name = re.sub(r'[\\/:*?"<>|]', '_', final_name)
                    max_len = 120
                    if len(final_name) > max_len:
                        final_name = final_name[:max_len]
                    final_name = f"{final_name}{ext}"
                    while final_name in used_names:
                        final_name = f"{os.path.splitext(final_name)[0]}-{uuid.uuid4().hex[:4]}{ext}"
                else:
                    base = storage_name or os.path.splitext(filename)[0]
                    base = re.sub(r'[\\/:*?"<>|]', '_', base)
                    final_name = f"{base}{ext}"
                    while final_name in used_names:
                        final_name = f"{base}-{uuid.uuid4().hex[:4]}{ext}"
                used_names.add(final_name)
                file_info.append({"name": final_name, "size": size})
                file_records.append(
                    {
                        "nombre_original": filename,
                        "nombre_final": final_name,
                        "size_bytes": size,
                    }
                )
                uploaded_files.append({"name": final_name, "content": content})

        archivos_html = '<ul>' + ''.join(
            f"<li>{r['nombre_final']} ({r['size_bytes']} bytes)</li>" for r in file_records
        ) + '</ul>'
        current_app.logger.info("Archivos listos para subir: %s", file_info)
        if not uploaded_files:
            flash('Debe subir al menos un archivo', 'error')
            return redirect(request.url)

        cfg = load_settings()
        mail_cfg = cfg.get('mail', {})
        drive_cfg = cfg.get('onedrive', {})
        raw_base = cat.get('base_path', '').strip()
        if not raw_base:
            current_app.logger.error('Categoría sin ruta base configurada')
            flash('Categoría sin ruta base configurada', 'error')
            return redirect(request.url)
        base_path = normalize_path(raw_base)
        recipients_cfg = cat.get('notify_emails', '').strip()
        cc_cfg = cat.get('notify_cc_emails', '').strip()
        bcc_cfg = cat.get('notify_bcc_emails', '').strip()

        missing = []
        if not mail_cfg.get('tested'):
            missing.append('correo')
        if not all(drive_cfg.get(k) for k in ('client_id', 'client_secret', 'tenant_id', 'user_id')):
            missing.append('credenciales de OneDrive')
        if not recipients_cfg and not cc_cfg and not bcc_cfg:
            missing.append('destinatarios')
        if missing:
            msg = ", ".join(missing)
            current_app.logger.error("Configuración incompleta: falta %s", msg)
            flash(f"Configuración incompleta: falta {msg}", 'error')
            return redirect(request.url)

        parts = base_path.split('/')
        if not parts or parts[-1].lower() != key.lower():
            cat_path = normalize_path(base_path, key)
        else:
            cat_path = base_path
        dest_dir = normalize_path(cat_path, nombre)
        if ':' in dest_dir or '\\' in dest_dir:
            current_app.logger.error("Ruta de OneDrive no válida: %s", dest_dir)
            flash(f"Ruta de OneDrive no válida: {dest_dir}", 'error')
            return redirect(request.url)
        current_app.logger.info("Ruta de OneDrive final: %s", dest_dir)

        to_recipients = [r.strip() for r in recipients_cfg.split(',') if r.strip()]
        cc_recipients = [r.strip() for r in cc_cfg.split(',') if r.strip()]
        bcc_recipients = [r.strip() for r in bcc_cfg.split(',') if r.strip()]
        if not to_recipients and not cc_recipients and not bcc_recipients:
            flash('No hay destinatarios configurados para esta categoría', 'error')
            return redirect(request.url)
        current_app.logger.info(
            "Destinatarios: to=%s cc=%s bcc=%s", to_recipients, cc_recipients, bcc_recipients
        )

        try:
            token = get_access_token(drive_cfg)
            current_app.logger.info("Token de Graph obtenido: %s", bool(token))
        except GraphAPIError as e:
            current_app.logger.exception("Error obteniendo token de Graph")
            flash(f"Error obteniendo token de Graph: {e}", 'error')
            return redirect(url_for('main.index'))

        test_mode = request.args.get('ab')
        current_app.logger.info("Modo A/B: %s", test_mode)

        status = "EXITO"
        error_detail = ""
        folder_url = ""
        if test_mode != 'B':
            try:
                folder_url = upload_files(
                    token, drive_cfg['user_id'], dest_dir, uploaded_files
                )
                current_app.logger.info("Archivos subidos a: %s", folder_url)
            except GraphAPIError as e:
                current_app.logger.exception("Error al subir archivos a OneDrive")
                status = "ERROR"
                error_detail = f"Error subiendo archivo a OneDrive: {e}"
                flash(f"Error subiendo archivo a OneDrive: {e}", 'error')
                save_log_entry(
                    categoria_key=key,
                    categoria_nombre=cat['name'],
                    solicitante_nombre=nombre,
                    solicitante_email=solicitante_email,
                    one_drive_path=dest_dir,
                    one_drive_folder_url=folder_url,
                    archivos=file_records,
                    estado=status,
                    detalle_error=error_detail,
                    destinatarios_to=to_recipients,
                    destinatarios_cc=cc_recipients,
                    user_admin="",
                )
                return redirect(url_for('main.index'))
        else:
            current_app.logger.info("Modo B: se omite la subida de archivos")

        if test_mode != 'A':
            vars_map = {
                'CATEGORIA': cat['name'],
                'CATEGORIA_KEY': key,
                'CARPETA_URL': folder_url,
                'ARCHIVOS_LISTA': archivos_html,
                'USUARIO_ADMIN': '',
            }
            vars_map.update(dynamic_vars)
            subject_template = cat.get('mail_subject_template', '')
            body_template = cat.get('mail_body_template', '')
            if subject_template or body_template:
                subject = render_text(subject_template, vars_map)
                body = render_text(body_template, vars_map)
            else:
                subject = f"Inscripción recibida: {nombre} - {cat['name']}"
                body = render_template(
                    'emails/inscripcion.html',
                    nombre=nombre,
                    categoria=cat['name'],
                    fields=form_values,
                    folder_link=folder_url,
                )
            try:
                send_mail_custom(
                    token,
                    drive_cfg['user_id'],
                    subject,
                    body,
                    to_recipients,
                    cc_recipients,
                    bcc_recipients,
                    uploaded_files,
                )
                flash('Inscripción completada: correo enviado', 'success')
            except GraphAPIError as e:
                current_app.logger.exception("Error enviando correo")
                status = "ERROR"
                error_detail = f"Error enviando correo: {e}"
                if test_mode == 'B':
                    flash(f"Error enviando correo: {e}", 'error')
                else:
                    flash(
                        f"Archivos subidos pero falló el envío de correo: {e}", 'error'
                    )
        else:
            flash('Archivos subidos sin enviar correo (modo A)', 'info')
        save_log_entry(
            categoria_key=key,
            categoria_nombre=cat['name'],
            solicitante_nombre=nombre,
            solicitante_email=solicitante_email,
            one_drive_path=dest_dir,
            one_drive_folder_url=folder_url,
            archivos=file_records,
            estado=status,
            detalle_error=error_detail,
            destinatarios_to=to_recipients,
            destinatarios_cc=cc_recipients,
            user_admin="",
        )

        return redirect(url_for('main.index'))

    return render_template('form.html', category_name=cat['name'], files=files_cfg, fields=fields)
