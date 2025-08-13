from django.contrib import admin
from .models import Setting, Category, FileField, TextField

admin.site.register(Setting)
admin.site.register(Category)
admin.site.register(FileField)
admin.site.register(TextField)
