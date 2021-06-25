import django_tables2 as tables
from . import models


class TransactionTable(tables.Table):
    class Meta:
        model = models.Transaction
        template_name = "tables/table.html"
        fields = ("transaction_date", "amount", )
        order_by = '-transaction_date'


class BuxferTransactionTable(tables.Table):
    class Meta:
        model = models.BuxferTransaction
        template_name = "tables/table.html"
        fields = ("transaction_date", "amount", )
        order_by = '-transaction_date'
