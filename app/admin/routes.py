import os
import csv
from flask import Blueprint, render_template, request, redirect, url_for, flash

from ..utils import load_menu, FILE_CONFIG, MENU_CONFIG

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/menu', methods=['GET', 'POST'])
def menu():
    menu = load_menu()
    if request.method == 'POST':
        key = request.form['key']
        name = request.form['name']
        parent = request.form['parent']
        with open(MENU_CONFIG, 'a', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow([key, name, parent])
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
