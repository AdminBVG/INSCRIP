import os
import uuid
import re
import logging
from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from django.conf import settings

from .utils import (
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

logger = logging.getLogger(__name__)


def index(request):
    setup_ok = is_setup_complete()
    logger.info("is_setup_complete: %s", setup_ok)
    if not setup_ok:
        messages.error(request, "Debe completar la configuración antes de continuar")
        return redirect("/admin/settings")
    menu = load_menu()
    roots = [i for i in menu if i['parent'] == '']
    return render(request, 'index.html', {'menu': roots, 'title': 'Inscripciones'})


def inscripcion(request, key):
    setup_ok = is_setup_complete()
    logger.info("is_setup_complete: %s", setup_ok)
    if not setup_ok:
        messages.error(request, "Debe completar la configuración antes de continuar")
        return redirect("/admin/settings")
    menu = load_menu()
    cat = next((i for i in menu if i['key'] == key), None)
    if not cat:
        messages.error(request, 'Categoría no encontrada')
        return redirect('index')

    children = [i for i in menu if i['parent'] == key]
    if children and request.method == 'GET':
        return render(request, 'index.html', {'menu': children, 'title': cat['name']})

    files_cfg = load_file_fields(key)
    fields = load_text_fields(key)

    if request.method == 'POST':
        logger.info("Inicio de inscripción: %s", key)
        logger.info("Datos de formulario: %s", dict(request.POST))
        logger.info(
            "Archivos recibidos: %s",
            {k: v.name for k, v in request.FILES.items()},
        )
        form_values = {}
        dynamic_vars = {}
        nombre = ''
        solicitante_email = ''
        for field in fields:
            value = request.POST.get(field['name'], '').strip()
            if field.get('required') and not value:
                messages.error(request, f"El campo {field['label']} es obligatorio")
                return redirect(request.path)
            form_values[field['label']] = value
            dynamic_vars[normalize_var(field['name'])] = value
            if field['name'] == 'nombre':
                nombre = value
            if field['name'] == 'email':
                solicitante_email = value
        if not nombre:
            messages.error(request, 'Debe incluir el campo nombre')
            return redirect(request.path)

        uploaded_files = []
        file_info = []
        file_records = []
        used_names = set()
        allowed_exts = [e.lower() for e in getattr(settings, 'UPLOAD_EXTENSIONS', [])]
        for fcfg in files_cfg:
            f = request.FILES.get(fcfg['name'])
            if fcfg.get('required') and (not f or f.name == ''):
                messages.error(request, f"El archivo {fcfg['label']} es obligatorio")
                return redirect(request.path)
            if f and f.name != '':
                filename = f.name
                ext = os.path.splitext(filename)[1].lower()
                if ext not in allowed_exts:
                    messages.error(request, f'Archivo no permitido: {filename}')
                    return redirect(request.path)
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
        logger.info("Archivos listos para subir: %s", file_info)
        if not uploaded_files:
            messages.error(request, 'Debe subir al menos un archivo')
            return redirect(request.path)

        cfg = load_settings()
        mail_cfg = cfg.get('mail', {})
        drive_cfg = cfg.get('onedrive', {})
        raw_base = cat.get('base_path', '').strip()
        if not raw_base:
            logger.error('Categoría sin ruta base configurada')
            messages.error(request, 'Categoría sin ruta base configurada')
            return redirect(request.path)
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
            logger.error("Configuración incompleta: falta %s", msg)
            messages.error(request, f"Configuración incompleta: falta {msg}")
            return redirect(request.path)

        parts = base_path.split('/')
        if not parts or parts[-1].lower() != key.lower():
            cat_path = normalize_path(base_path, key)
        else:
            cat_path = base_path
        dest_dir = normalize_path(cat_path, nombre)
        if ':' in dest_dir or '\\' in dest_dir:
            logger.error("Ruta de OneDrive no válida: %s", dest_dir)
            messages.error(request, f"Ruta de OneDrive no válida: {dest_dir}")
            return redirect(request.path)
        logger.info("Ruta de OneDrive final: %s", dest_dir)

        to_recipients = [r.strip() for r in recipients_cfg.split(',') if r.strip()]
        cc_recipients = [r.strip() for r in cc_cfg.split(',') if r.strip()]
        bcc_recipients = [r.strip() for r in bcc_cfg.split(',') if r.strip()]
        if not to_recipients and not cc_recipients and not bcc_recipients:
            messages.error(request, 'No hay destinatarios configurados para esta categoría')
            return redirect(request.path)
        logger.info(
            "Destinatarios: to=%s cc=%s bcc=%s", to_recipients, cc_recipients, bcc_recipients
        )

        try:
            token = get_access_token(drive_cfg)
            logger.info("Token de Graph obtenido: %s", bool(token))
        except GraphAPIError as e:
            logger.exception("Error obteniendo token de Graph")
            messages.error(request, f"Error de autenticación: {e}")
            return redirect(request.path)

        folder_url = ''
        try:
            folder_url = upload_files(token, dest_dir, uploaded_files)
            logger.info("Archivos subidos a OneDrive: %s", folder_url)
        except Exception as e:
            logger.exception("Error subiendo archivos a OneDrive")
            save_log_entry(
                categoria_key=cat['key'],
                categoria_nombre=cat['name'],
                solicitante_nombre=nombre,
                solicitante_email=solicitante_email,
                one_drive_path=dest_dir,
                one_drive_folder_url=folder_url,
                archivos=file_records,
                estado='ERROR_ONEDRIVE',
                detalle_error=str(e),
                destinatarios_to=to_recipients,
                destinatarios_cc=cc_recipients,
                user_admin='',
            )
            messages.error(request, f"Error subiendo archivos: {e}")
            return redirect(request.path)

        vars_map = {
            'CATEGORIA': cat['name'],
            'CATEGORIA_KEY': cat['key'],
            'CARPETA_URL': folder_url,
            'ARCHIVOS_LISTA': archivos_html,
            'USUARIO_ADMIN': '',
        }
        for k, v in dynamic_vars.items():
            vars_map[k] = v
        rendered_subject = render_text(cat.get('mail_subject_template', ''), vars_map)
        rendered_body = render_text(cat.get('mail_body_template', ''), vars_map)
        try:
            send_mail_custom(
                mail_cfg,
                to_recipients,
                rendered_subject,
                rendered_body,
                cc_recipients,
                bcc_recipients,
            )
            status = 'ENVIADO'
            messages.success(request, 'Inscripción completada')
        except Exception as e:
            logger.exception("Error enviando correo")
            status = 'ERROR_MAIL'
            messages.error(request, f"Error enviando correo: {e}")

        save_log_entry(
            categoria_key=cat['key'],
            categoria_nombre=cat['name'],
            solicitante_nombre=nombre,
            solicitante_email=solicitante_email,
            one_drive_path=dest_dir,
            one_drive_folder_url=folder_url,
            archivos=file_records,
            estado=status,
            detalle_error=''
            if status == 'ENVIADO'
            else 'Error en correo',
            destinatarios_to=to_recipients,
            destinatarios_cc=cc_recipients,
            user_admin='',
        )

        return redirect('index')

    return render(
        request,
        'form.html',
        {
            'cat': cat,
            'files_cfg': files_cfg,
            'fields': fields,
            'upload_exts': getattr(settings, 'UPLOAD_EXTENSIONS', []),
        },
    )
