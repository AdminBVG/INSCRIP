from datetime import datetime
from .db import SessionLocal
from .models import Category, FileField, TextField, Submission, Setting


def load_menu(include_inactive: bool = False):
    """Return list of categories.

    Args:
        include_inactive: When True include inactive categories.
    """
    with SessionLocal() as db:
        query = db.query(Category)
        if not include_inactive:
            query = query.filter_by(active=True)
        categories = query.all()
        result = []
        for c in categories:
            result.append(
                {
                    'id': c.id,
                    'key': c.key,
                    'name': c.name,
                    'parent': c.parent.key if c.parent else '',
                    'parent_id': c.parent_id,
                    'base_path': c.base_path,
                    'notify_emails': c.notify_emails,
                    'notify_cc_emails': c.notify_cc_emails,
                    'active': c.active,
                }
            )
        return result


def load_file_fields(cat_key: str) -> list:
    with SessionLocal() as db:
        cat = db.query(Category).filter_by(key=cat_key).first()
        if not cat:
            return []
        fields = (
            db.query(FileField)
            .filter_by(category_id=cat.id)
            .order_by(FileField.order)
            .all()
        )
        return [
            {
                'name': f.name,
                'label': f.label,
                'description': f.description,
                'required': f.required,
            }
            for f in fields
        ]


def save_file_fields(cat_key: str, files: list) -> None:
    with SessionLocal() as db:
        cat = db.query(Category).filter_by(key=cat_key).first()
        if not cat:
            return
        db.query(FileField).filter_by(category_id=cat.id).delete()
        for idx, f in enumerate(files):
            db.add(FileField(category_id=cat.id, order=idx, **f))
        db.commit()


def load_text_fields(cat_key: str) -> list:
    with SessionLocal() as db:
        cat = db.query(Category).filter_by(key=cat_key).first()
        if not cat:
            return []
        fields = (
            db.query(TextField)
            .filter_by(category_id=cat.id)
            .order_by(TextField.order)
            .all()
        )
        return [
            {
                'name': f.name,
                'label': f.label,
                'type': f.type,
                'required': f.required,
            }
            for f in fields
        ]


def save_text_fields(cat_key: str, fields: list) -> None:
    with SessionLocal() as db:
        cat = db.query(Category).filter_by(key=cat_key).first()
        if not cat:
            return
        db.query(TextField).filter_by(category_id=cat.id).delete()
        for idx, f in enumerate(fields):
            db.add(TextField(category_id=cat.id, order=idx, **f))
        db.commit()


def save_submission(
    cat_key: str,
    fields: dict,
    files: list,
    folder_url: str,
    status: str,
    error: str = "",
    user: str = "",
) -> None:
    with SessionLocal() as db:
        cat = db.query(Category).filter_by(key=cat_key).first()
        db.add(
            Submission(
                category_id=cat.id if cat else None,
                fields=fields,
                files=files,
                folder_url=folder_url,
                status=status,
                error=error,
                user=user,
                created_at=datetime.utcnow(),
            )
        )
        db.commit()


def load_submissions(cat_key: str = '') -> list:
    with SessionLocal() as db:
        query = db.query(Submission)
        if cat_key:
            cat = db.query(Category).filter_by(key=cat_key).first()
            if not cat:
                return []
            query = query.filter_by(category_id=cat.id)
        subs = query.order_by(Submission.created_at.desc()).all()
        result = []
        for s in subs:
            result.append(
                {
                    'category': s.category.key if s.category else '',
                    'fields': s.fields,
                    'files': s.files,
                    'folder_url': s.folder_url,
                    'status': s.status,
                    'error': s.error,
                    'user': s.user,
                    'created_at': s.created_at.isoformat() if s.created_at else '',
                }
            )
        return result


def load_settings():
    with SessionLocal() as db:
        settings = {s.section: s.data for s in db.query(Setting).all()}
    defaults = {
        "mail": {
            "mail_user": "",
            "mail_password": "",
            "smtp_host": "smtp.office365.com",
            "smtp_port": 587,
            "tested": False,
            "updated_at": "",
            "tested_at": "",
        },
        "onedrive": {
            "client_id": "",
            "client_secret": "",
            "tenant_id": "",
            "user_id": "",
            "tested": False,
            "updated_at": "",
            "tested_at": "",
        },
    }
    for section, values in defaults.items():
        settings.setdefault(section, {})
        for k, v in values.items():
            settings[section].setdefault(k, v)
    return settings


def save_settings(data):
    with SessionLocal() as db:
        for section, values in data.items():
            obj = db.query(Setting).filter_by(section=section).first()
            if obj:
                obj.data = values
            else:
                obj = Setting(section=section, data=values)
                db.add(obj)
        db.commit()


def is_setup_complete():
    settings = load_settings()
    mail = settings.get('mail', {})
    drive = settings.get('onedrive', {})
    with SessionLocal() as db:
        menu_ok = db.query(Category).first() is not None
    mail_ok = mail.get('tested')
    drive_ok = drive.get('tested') and all(
        drive.get(k) for k in ('client_id', 'client_secret', 'tenant_id', 'user_id')
    )
    return mail_ok and drive_ok and menu_ok
