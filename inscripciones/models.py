from django.db import models


class Category(models.Model):
    key = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    base_path = models.CharField(max_length=255, blank=True, default='')
    notify_emails = models.CharField(max_length=255, blank=True, default='')
    notify_cc_emails = models.CharField(max_length=255, blank=True, default='')
    notify_bcc_emails = models.CharField(max_length=255, blank=True, default='')
    mail_subject_template = models.CharField(max_length=255, blank=True, default='')
    mail_body_template = models.TextField(blank=True, default='')
    file_pattern = models.CharField(max_length=255, blank=True, default='')
    active = models.BooleanField(default=True)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children', on_delete=models.SET_NULL)

    def __str__(self):
        return self.name


class FileField(models.Model):
    category = models.ForeignKey(Category, related_name='file_fields', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    label = models.CharField(max_length=200)
    description = models.CharField(max_length=255, blank=True, default='')
    storage_name = models.CharField(max_length=255, blank=True, default='')
    required = models.BooleanField(default=False)
    order = models.IntegerField(default=0)


class TextField(models.Model):
    category = models.ForeignKey(Category, related_name='text_fields', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    label = models.CharField(max_length=200)
    type = models.CharField(max_length=50, default='text')
    required = models.BooleanField(default=False)
    order = models.IntegerField(default=0)


class Setting(models.Model):
    section = models.CharField(max_length=100, primary_key=True)
    data = models.JSONField()


class Submission(models.Model):
    category = models.ForeignKey(Category, null=True, on_delete=models.SET_NULL)
    fields = models.JSONField()
    files = models.JSONField()
    folder_url = models.CharField(max_length=255, blank=True, default='')
    status = models.CharField(max_length=100, blank=True, default='')
    error = models.CharField(max_length=255, blank=True, default='')
    user = models.CharField(max_length=100, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)


class LogEntry(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    categoria_key = models.CharField(max_length=100)
    categoria_nombre = models.CharField(max_length=200)
    solicitante_nombre = models.CharField(max_length=200)
    solicitante_email = models.CharField(max_length=255, blank=True, default='')
    one_drive_path = models.CharField(max_length=255, blank=True, default='')
    one_drive_folder_url = models.CharField(max_length=255, blank=True, default='')
    archivos = models.JSONField()
    estado = models.CharField(max_length=50)
    detalle_error = models.TextField(blank=True, null=True)
    destinatarios_to = models.JSONField(default=list, blank=True)
    destinatarios_cc = models.JSONField(default=list, blank=True)
    user_admin = models.CharField(max_length=100, blank=True, default='')
