import django_tables2 as tables
from django_tables2 import A

from . import models


class TransactionTable(tables.Table):
    bank_transaction_id = tables.LinkColumn('bank_detail', args=[A('pk')])
    class Meta:
        model = models.Transaction
        template_name = "tables/table.html"
        fields = ("bank_transaction_id", "transaction_date", "amount", "uploaded_to_buxfer")
        order_by = '-transaction_date'


class BuxferTransactionTable(tables.Table):
    class Meta:
        model = models.BuxferTransaction
        template_name = "tables/table.html"
        fields = ("transaction_date", "amount", )
        order_by = '-transaction_date'
