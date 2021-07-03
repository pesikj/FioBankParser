from django.contrib import admin
from . import models

admin.site.register(models.Transaction)
admin.site.register(models.BankProfile)
admin.site.register(models.BuxferTransaction)
admin.site.register(models.BankAccount)
admin.site.register(models.AutoTaggingString)
