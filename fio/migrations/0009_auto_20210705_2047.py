# Generated by Django 3.2.5 on 2021-07-05 20:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('fio', '0008_bankaccount_cash'),
    ]

    operations = [
        migrations.RenameField(
            model_name='buxfertransaction',
            old_name='account_id',
            new_name='buxfer_account_id',
        ),
        migrations.RenameField(
            model_name='buxfertransaction',
            old_name='account_name',
            new_name='buxfer_account_name',
        ),
        migrations.AddField(
            model_name='buxfertransaction',
            name='account',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='buxfer_transaction_account', to='fio.bankaccount'),
        ),
        migrations.AlterField(
            model_name='buxfertransaction',
            name='from_account',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='buxfer_transaction_from_account', to='fio.bankaccount'),
        ),
        migrations.AlterField(
            model_name='buxfertransaction',
            name='to_account',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='buxfer_transaction_to_account', to='fio.bankaccount'),
        ),
    ]
