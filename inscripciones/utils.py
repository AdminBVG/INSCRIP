from typing import Dict, Any, List
from .models import Category, FileField, TextField, Setting, LogEntry


def load_menu(include_inactive: bool = False) -> List[Dict[str, Any]]:
    qs = Category.objects.all()
    if not include_inactive:
        qs = qs.filter(active=True)
    result = []
    for c in qs.select_related('parent'):
        result.append({
            'id': c.id,
            'key': c.key,
            'name': c.name,
            'parent': c.parent.key if c.parent else '',
            'parent_id': c.parent_id,
            'base_path': c.base_path,
            'notify_emails': c.notify_emails,
            'notify_cc_emails': c.notify_cc_emails,
            'notify_bcc_emails': c.notify_bcc_emails,
            'mail_subject_template': c.mail_subject_template,
            'mail_body_template': c.mail_body_template,
            'file_pattern': c.file_pattern,
            'active': c.active,
        })
    return result


def load_file_fields(cat_key: str) -> List[Dict[str, Any]]:
    try:
        cat = Category.objects.get(key=cat_key)
    except Category.DoesNotExist:
        return []
    fields = cat.file_fields.order_by('order')
    return [
        {
            'name': f.name,
            'label': f.label,
            'description': f.description,
            'required': f.required,
            'storage_name': f.storage_name,
        }
        for f in fields
    ]


def load_text_fields(cat_key: str) -> List[Dict[str, Any]]:
    try:
        cat = Category.objects.get(key=cat_key)
    except Category.DoesNotExist:
        return []
    fields = cat.text_fields.order_by('order')
    return [
        {
            'name': f.name,
            'label': f.label,
            'type': f.type,
            'required': f.required,
        }
        for f in fields
    ]


def load_settings() -> Dict[str, Dict[str, Any]]:
    settings = {s.section: s.data for s in Setting.objects.all()}
    defaults = {
        'mail': {
            'mail_user': '',
            'mail_password': '',
            'smtp_host': 'smtp.office365.com',
            'smtp_port': 587,
            'tested': False,
            'updated_at': '',
            'tested_at': '',
        },
        'onedrive': {
            'client_id': '',
            'client_secret': '',
            'tenant_id': '',
            'user_id': '',
            'tested': False,
            'updated_at': '',
            'tested_at': '',
        },
    }
    for section, values in defaults.items():
        settings.setdefault(section, {})
        for k, v in values.items():
            settings[section].setdefault(k, v)
    return settings


def is_setup_complete() -> bool:
    """Verifica si el sistema cuenta con la configuración mínima necesaria.

    Antes se requería que las configuraciones de correo y Microsoft Graph
    estuvieran marcadas como "testeadas". Esto provocaba que, tras guardar
    los valores en el panel de administración, el sitio quedara bloqueado
    hasta ejecutar una prueba manual. Ahora solo se valida que existan los
    datos básicos requeridos, permitiendo que el flujo de inscripción
    continúe inmediatamente después de guardar la configuración.
    """

    settings = load_settings()
    mail = settings.get('mail', {})
    drive = settings.get('onedrive', {})
    menu_ok = Category.objects.exists()

    # Correo configurado si usuario y contraseña están definidos
    mail_ok = bool(mail.get('mail_user') and mail.get('mail_password'))

    # Credenciales de Graph/OneDrive completas
    drive_ok = all(
        drive.get(k) for k in ('client_id', 'client_secret', 'tenant_id', 'user_id')
    )

    return menu_ok and mail_ok and drive_ok


def save_log_entry(**data) -> None:
    LogEntry.objects.create(**data)
