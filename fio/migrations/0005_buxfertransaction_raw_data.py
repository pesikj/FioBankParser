# Generated by Django 3.2.5 on 2021-07-05 08:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fio', '0004_autotaggingstring_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='buxfertransaction',
            name='raw_data',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
