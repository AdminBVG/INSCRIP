# INSCRIP

Sistema de inscripción que permite definir categorías y subcategorías con campos y archivos personalizados. Las configuraciones y envíos se almacenan en una base de datos PostgreSQL.

## Requisitos
- Python 3.11+
- PostgreSQL 14+
- Dependencias de Python indicadas en `requirements.txt` (instalar con `pip install -r requirements.txt`)

## Configuración de la base de datos
1. Crear una base de datos en PostgreSQL:
   ```sql
   CREATE DATABASE inscrip;
   ```
2. Definir la variable de entorno `DATABASE_URL` apuntando a la base de datos:
   ```bash
   export DATABASE_URL=postgresql+psycopg2://usuario:password@localhost/inscrip
   ```
3. Al iniciar la aplicación se crearán automáticamente las tablas necesarias.

## Ejecución
### Desarrollo
1. Instalar dependencias.
2. Configurar `DATABASE_URL` como se indicó.
3. Ejecutar la aplicación:
   ```bash
   flask --app app.py run
   ```

### Producción
- Utilizar un servidor WSGI como Gunicorn y un proxy inverso (Nginx).
- Asegurar que las variables de entorno se encuentren definidas.
- Configurar HTTPS y un sistema de logs.

## Notas de seguridad
- Nunca almacenar credenciales en el repositorio. Utilizar variables de entorno o un gestor de secretos.
- Probar las credenciales de SMTP y Microsoft Graph desde la sección de configuración del panel de administración.
- Limitar el tamaño de los archivos subidos y validar extensiones permitidas.

## Mantenimiento
- Realizar respaldos periódicos de la base de datos (`pg_dump inscrip > backup.sql`).
- Para cambios en el esquema utilizar migraciones con herramientas como Alembic.
- Revisar los registros de correo y de Graph para detectar fallas en el envío de inscripciones.
