import os, csv
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from services.onedrive import upload_files
from services.mail import send_mail

# Cargar variables de entorno
load_dotenv()

# Configuración CSV
MENU_CONFIG = 'menu_config.csv'
FILE_CONFIG = 'file_config.csv'

def init_configs():
    if not os.path.exists(MENU_CONFIG):
        with open(MENU_CONFIG, 'w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(['emisores','EMISORES',''])
    if not os.path.exists(FILE_CONFIG):
        with open(FILE_CONFIG, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['category_key','file_label'])
            writer.writerow(['emisores','Archivo 1'])

def load_menu():
    items = []
    with open(MENU_CONFIG, newline='', encoding='utf-8') as f:
        for key,name,parent in csv.reader(f):
            items.append({'key':key,'name':name,'parent':parent})
    return items

def load_file_labels(cat):
    labels = []
    with open(FILE_CONFIG, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r['category_key'] == cat:
                labels.append(r['file_label'])
    return labels

app = Flask(__name__)
app.secret_key = 'clave-secreta'

# Inicializar configuraciones al arranque
init_configs()

@app.route('/')
def index():
    menu = load_menu()
    roots = [i for i in menu if i['parent']=='']
    return render_template('index.html', menu=roots)

@app.route('/inscripcion/<key>', methods=['GET','POST'])
def inscripcion(key):
    menu = load_menu()
    cat = next((i for i in menu if i['key']==key), None)
    if not cat:
        flash('Categoría no encontrada')
        return redirect(url_for('index'))

    labels = load_file_labels(key)

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        if not nombre:
            flash('El nombre es obligatorio')
            return redirect(request.url)

        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            flash('Debe subir al menos un archivo')
            return redirect(request.url)

        try:
            folder_path, file_links = upload_files(nombre, key, files)
            send_mail(nombre, key, file_links)
            flash('Enviado correctamente')
        except Exception as e:
            flash(f'Error: {str(e)}')

        return redirect(url_for('index'))

    return render_template('form.html', category_name=cat['name'], labels=labels)

@app.route('/admin/menu', methods=['GET','POST'])
def admin_menu():
    menu = load_menu()
    if request.method == 'POST':
        key = request.form['key']
        name = request.form['name']
        parent = request.form['parent']
        with open(MENU_CONFIG, 'a', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow([key,name,parent])
        flash('Menú actualizado')
        return redirect(url_for('admin_menu'))
    return render_template('admin_menu.html', menu=menu)

@app.route('/admin/files', methods=['GET','POST'])
def admin_files():
    menu = load_menu()
    labels = []
    if request.method == 'POST':
        cat = request.form['category']
        labels = request.form['labels'].split(',')
        rows=[]
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
            writer.writerow(['category_key','file_label'])
            writer.writerows(rows)
        flash('Archivos actualizados')
        return redirect(url_for('admin_files'))
    return render_template('admin_files.html', menu=menu, labels=labels)

if __name__ == '__main__':
    app.run(debug=True)