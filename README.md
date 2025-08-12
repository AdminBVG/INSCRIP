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

## Configuración de categorías y rutas
1. Ingrese al panel de administración (`/admin`).
2. Cree o edite una categoría y defina:
   - **Destinatarios** (`notify_emails`, `notify_cc_emails`, `notify_bcc_emails`): listas de correos separados por coma.
   - **Ruta base de OneDrive** (`base_path`): carpeta relativa donde se guardarán los archivos (ej. `Inscripciones`).
     No utilice rutas absolutas como `C:\Usuarios`.
   - **Plantilla de correo**: asunto y cuerpo personalizados con variables dinámicas.
3. Guarde los cambios.

La ruta final en OneDrive se construye como `base_path/categoria/nombre`.

### Configuración de archivos
En `/admin/files` puede definirse para cada archivo requerido un **Nombre final**. Este valor se utiliza para renombrar el archivo al almacenarlo y también al reemplazar la variable `{label}` en el patrón de nombres configurado en la categoría.

### Plantillas de correo
Cada categoría puede tener su propia plantilla de correo editable desde la interfaz de administración. El administrador puede definir los destinatarios To/CC/BCC, el asunto y el cuerpo (HTML o Markdown simple) e insertar variables dinámicas mediante botones. También es posible previsualizar y enviar un correo de prueba antes de guardar.

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

## Troubleshooting
- Revise los logs generados por Flask para identificar fallos de configuración, ruta de OneDrive o credenciales.
- Asegúrese de que cada categoría tenga destinatarios configurados y que los archivos cargados tengan extensiones permitidas.
- Verifique que la ruta base de OneDrive sea relativa y no contenga `:` ni `\`.
- Puede enviar el formulario con `?ab=A` para subir archivos sin enviar correo o `?ab=B` para enviar correo sin subir archivos.

## Funcionalidades de Test
En el menú principal se añadió la opción **Test** con dos herramientas:
- **Probar envío de correo:** formulario para enviar un correo de prueba utilizando la configuración actual (SMTP o Microsoft Graph). Muestra mensajes claros de éxito o error.
- **Probar guardado en OneDrive:** permite subir un archivo a la carpeta configurada para verificar permisos y conectividad.

## Notas de seguridad
- Mantener las credenciales fuera del control de versiones.
- Validar el tamaño y extensión de los archivos cargados.
- Revisar regularmente los registros de errores.
