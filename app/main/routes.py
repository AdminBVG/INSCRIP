import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename

from ..utils import load_menu, load_file_labels, load_text_fields, is_setup_complete
from services.onedrive import upload_files
from services.mail import send_mail

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    if not is_setup_complete():
        flash('Debe completar la configuración antes de continuar')
        return redirect(url_for('admin.settings'))
    menu = load_menu()
    roots = [i for i in menu if i['parent'] == '']
    return render_template('index.html', menu=roots)


@main_bp.route('/inscripcion/<key>', methods=['GET', 'POST'])
def inscripcion(key):
    if not is_setup_complete():
        flash('Debe completar la configuración antes de continuar')
        return redirect(url_for('admin.settings'))
    menu = load_menu()
    cat = next((i for i in menu if i['key'] == key), None)
    if not cat:
        flash('Categoría no encontrada')
        return redirect(url_for('main.index'))

    labels = load_file_labels(key)
    fields = load_text_fields(key)

    if request.method == 'POST':
        form_values = {}
        nombre = ''
        for field in fields:
            value = request.form.get(field['name'], '').strip()
            if field.get('required') and not value:
                flash(f"El campo {field['label']} es obligatorio")
                return redirect(request.url)
            form_values[field['label']] = value
            if field['name'] == 'nombre':
                nombre = value
        if not nombre:
            flash('Debe incluir el campo nombre')
            return redirect(request.url)

        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            flash('Debe subir al menos un archivo')
            return redirect(request.url)

        allowed_exts = current_app.config['UPLOAD_EXTENSIONS']
        for f in files:
            filename = secure_filename(f.filename)
            ext = os.path.splitext(filename)[1].lower()
            if ext not in allowed_exts:
                flash(f'Archivo no permitido: {filename}')
                return redirect(request.url)

        try:
            folder_path, file_links = upload_files(nombre, key, cat.get('base_path', 'Inscripciones'), files)
            send_mail(nombre, cat['name'], form_values, file_links)
            flash('Enviado correctamente')
        except Exception as e:
            flash(f'Error: {str(e)}')
        return redirect(url_for('main.index'))

    return render_template('form.html', category_name=cat['name'], labels=labels, fields=fields)
