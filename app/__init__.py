import os
from flask import Flask
from .db import init_db
from .main.routes import main_bp
from .admin.routes import admin_bp


def create_app():
    app = Flask(__name__, template_folder='../templates')
    app.secret_key = os.getenv('SECRET_KEY', 'clave-secreta')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB
    app.config['UPLOAD_EXTENSIONS'] = ['.pdf', '.png', '.jpg', '.jpeg']

    init_db()
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    return app
