from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from django.db.models import Deferrable, UniqueConstraint

UniqueConstraint(
    name='unique_bank_transaction_id',
    fields=['bank_transaction_id'],
    deferrable=Deferrable.DEFERRED,
)

UniqueConstraint(
    name='unique_buxfer_id',
    fields=['buxfer_id'],
    deferrable=Deferrable.DEFERRED,
)


class Transaction(models.Model):
    transaction_date = models.DateField()
    amount = models.DecimalField(decimal_places=2, max_digits=12)
    contra_account = models.CharField(max_length=20, null=True, blank=True)
    contra_account_bank_code = models.CharField(max_length=6, null=True, blank=True)
    constant_symbol = models.CharField(max_length=10, null=True, blank=True)
    variable_code = models.CharField(max_length=12, null=True, blank=True)
    user_identification = models.CharField(max_length=200, null=True, blank=True)
    bank_transaction_type = models.CharField(max_length=200, null=True, blank=True)
    bank_name = models.CharField(max_length=100, null=True, blank=True)
    currency = models.CharField(max_length=20, null=True, blank=True)
    receiver_message = models.CharField(max_length=200, null=True, blank=True)
    request_id = models.BigIntegerField(unique=True)
    bank_transaction_id = models.BigIntegerField(unique=True)
    comment = models.CharField(max_length=200, null=True, blank=True)

    @property
    def uploaded_to_buxfer(self):
        return self.buxfertransaction.pk is not None


class BuxferTransaction(models.Model):
    buxfer_id = models.BigIntegerField(unique=True, null=True, blank=True)
    description = models.CharField(max_length=200, null=True, blank=True)
    bank_transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, null=True, blank=True)
    transaction_date = models.DateField(null=True, blank=True)
    transaction_type = models.CharField(max_length=20, null=True, blank=True)
    amount = models.DecimalField(decimal_places=2, max_digits=12, null=True, blank=True)
    expense_amount = models.DecimalField(decimal_places=2, max_digits=12, null=True, blank=True)
    account_id = models.BigIntegerField(null=True, blank=True)
    account_name = models.CharField(max_length=200, null=True, blank=True)
    tags = models.CharField(max_length=200, null=True, blank=True)
    tag_names = models.CharField(max_length=200, null=True, blank=True)
    status = models.CharField(max_length=20, null=True, blank=True)
    is_future_dated = models.BooleanField(null=True, blank=True)
    is_pending = models.BooleanField(null=True, blank=True)


class BankProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    fio_bank_token = models.CharField(max_length=100, blank=True)
    buxfer_username = models.CharField(max_length=100, blank=True)
    buxfer_password = models.CharField(max_length=100, blank=True)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        BankProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
