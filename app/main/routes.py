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
from services.graph_auth import GraphAPIError


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    if not is_setup_complete():
        flash('Debe completar la configuración antes de continuar', 'error')
        return redirect(url_for('admin.settings'))
    menu = load_menu()
    roots = [i for i in menu if i['parent'] == '']
    return render_template('index.html', menu=roots, title='Inscripciones')


@main_bp.route('/inscripcion/<key>', methods=['GET', 'POST'])
def inscripcion(key):
    if not is_setup_complete():
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
        base_path = cat.get('base_path') or cfg['onedrive'].get('base_path', 'Inscripciones')

        try:
            folder_path, file_links = upload_files(
                nombre, key, base_path, uploaded_files
            )
            save_submission(key, form_values, file_links)
        except GraphAPIError as e:
            logger.exception("Error al subir archivos a OneDrive")
            flash(f"Error al subir archivos: {e}", 'error')
            return redirect(url_for('main.index'))
        except Exception as e:
            logger.exception("Error inesperado al subir archivos")
            flash(f"Error inesperado al subir archivos: {e}", 'error')
            return redirect(url_for('main.index'))

        try:
            send_mail(
                nombre,
                cat['name'],
                form_values,
                file_links,
                cat.get('notify_emails', ''),
            )
        except Exception as e:
            logger.exception("Error enviando correo")
            flash(f"Inscripción guardada pero no se pudo enviar el correo: {e}", 'error')
        else:
            flash('Inscripción guardada, archivos subidos y correo enviado', 'success')

        return redirect(url_for('main.index'))

    return render_template('form.html', category_name=cat['name'], files=files_cfg, fields=fields)
