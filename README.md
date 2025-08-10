# INSCRIP

Sistema de inscripciones desarrollado con Flask. Permite definir categorías con campos dinámicos, almacenar archivos en OneDrive mediante Microsoft Graph y enviar notificaciones por correo.

## Requisitos previos
- Python 3.11+
- PostgreSQL 14+
- Dependencias de Python listadas en `requirements.txt`

## Instalación
### Clonar el repositorio
```bash
git clone <REPO_URL>
cd INSCRIP
```

### Crear entorno virtual (opcional)
```bash
python -m venv venv
source venv/bin/activate
```

### Instalar dependencias
```bash
pip install -r requirements.txt
```

## Variables de entorno
| Variable | Descripción |
|---------|-------------|
| `DATABASE_URL` | Cadena de conexión de SQLAlchemy. Ej: `postgresql+psycopg2://usuario:pass@localhost/inscrip` |
| `SECRET_KEY` | Clave secreta de Flask |
| `CLIENT_ID` | ID de la aplicación en Azure AD |
| `CLIENT_SECRET` | Secreto de cliente en Azure AD |
| `TENANT_ID` | Tenant ID de Azure AD |
| `USER_ID` | Cuenta de OneDrive utilizada para las operaciones |
| `MAIL_USER` | (Opcional) correo Microsoft 365 para SMTP |
| `MAIL_PASSWORD` | (Opcional) contraseña del correo |
| `SMTP_HOST` | (Opcional) host SMTP. Por defecto `smtp.office365.com` |
| `SMTP_PORT` | (Opcional) puerto SMTP. Por defecto `587` |

Las variables pueden definirse en el entorno o en un archivo `.env` (no versionado).

## Inicialización de la base de datos
```bash
python -c "from app.db import init_db; init_db()"
```
La aplicación también crea las tablas automáticamente al iniciar.

## Ejecución
### Desarrollo
```bash
export FLASK_DEBUG=1  # opcional
flask --app app.py run
```

### Producción
Usar un servidor WSGI como Gunicorn:
```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```
Configurar un proxy reverso (Nginx) y habilitar HTTPS.

## Funcionalidades de Test
En el menú principal se añadió la opción **Test** con dos herramientas:
- **Probar envío de correo:** formulario para enviar un correo de prueba utilizando la configuración actual (SMTP o Microsoft Graph). Muestra mensajes claros de éxito o error.
- **Probar guardado en OneDrive:** permite subir un archivo a la carpeta configurada para verificar permisos y conectividad.

## Notas de seguridad
- Mantener las credenciales fuera del control de versiones.
- Validar el tamaño y extensión de los archivos cargados.
- Revisar regularmente los registros de errores.
