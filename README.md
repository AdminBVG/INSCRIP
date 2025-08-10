# INSCRIP

Sistema de inscripción en Flask que permite definir categorías y subcategorías con campos y archivos personalizados.
Las configuraciones y envíos se almacenan en una base de datos PostgreSQL y los archivos se guardan en OneDrive
usando Microsoft Graph.

## Requisitos previos
- Python 3.11 o superior
- PostgreSQL 14 o superior
- Dependencias de Python: Flask, SQLAlchemy, requests y python-dotenv (instalables con `pip`)

## Instalación
### 1. Clonar el repositorio
```bash
git clone <REPO_URL>
cd INSCRIP
```

### 2. Instalar dependencias
#### Con entorno virtual (recomendado)
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Sin entorno virtual
```bash
pip install -r requirements.txt
```

## Configuración de variables de entorno
| Variable | Descripción |
| --- | --- |
| `DATABASE_URL` | Cadena de conexión de SQLAlchemy (`postgresql+psycopg2://usuario:pass@localhost/inscrip`) |
| `SECRET_KEY` | Clave secreta de Flask |
| `MAIL_USER` | Cuenta de correo Microsoft 365 |
| `MAIL_PASSWORD` | Contraseña del correo |
| `SMTP_HOST` | Host SMTP (por defecto `smtp.office365.com`) |
| `SMTP_PORT` | Puerto SMTP (por defecto `587`) |
| `GRAPH_CLIENT_ID` | ID de aplicación en Azure |
| `GRAPH_CLIENT_SECRET` | Secreto de cliente en Azure |
| `GRAPH_TENANT_ID` | Tenant ID de Azure |
| `GRAPH_USER_ID` | Usuario de OneDrive que recibirá los archivos |

> Las credenciales se pueden almacenar en un archivo `.env` no versionado.

## Inicializar la base de datos
```bash
python -c "from app.db import init_db; init_db()"
```
Al ejecutar la aplicación también se crean las tablas si no existen.

## Ejecución
### Desarrollo
```bash
export FLASK_DEBUG=1  # opcional
flask --app app.py run
```

### Producción
Utilizar un servidor WSGI como Gunicorn:
```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```
Colocar un proxy reverso (Nginx) y habilitar HTTPS.

## Notas de seguridad
- No subir credenciales al repositorio; usar variables de entorno o gestor de secretos.
- Limitar el tamaño de archivos y validar extensiones permitidas.
- Revisar periódicamente los registros de errores.

## Errores comunes
| Problema | Solución |
| --- | --- |
| `SECRET_KEY no configurada` | Definir la variable `SECRET_KEY` antes de iniciar la aplicación. |
| Error de conexión a la base de datos | Verificar `DATABASE_URL` y que PostgreSQL esté ejecutándose. |
| `Graph API error 401` | Revisar credenciales de Azure (`GRAPH_*`). |
| Falla al enviar correo | Probar configuración SMTP desde el panel de administración y revisar `MAIL_*`. |

