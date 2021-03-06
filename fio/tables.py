import django_tables2 as tables
from django_tables2 import A

from . import models


class TransactionTable(tables.Table):
    bank_transaction_id = tables.LinkColumn('bank_detail', args=[A('pk')])

    class Meta:
        model = models.Transaction
        template_name = "tables/table.html"
        fields = ("bank_transaction_id", "transaction_date", "amount", "uploaded_to_buxfer", "description")
        order_by = '-transaction_date'


class BuxferTransactionTable(tables.Table):
    buxfer_id = tables.LinkColumn('buxfer_detail', args=[A('pk')])

    class Meta:
        model = models.BuxferTransaction
        template_name = "tables/table.html"
        fields = ("buxfer_id", "transaction_date", "amount", "transaction_type", "tags")
        order_by = '-transaction_date'


class AccountBalanceTable(tables.Table):
    date = tables.LinkColumn('account_balance_detail', args=[A('pk')])

    class Meta:
        model = models.AccountBalance
        template_name = "tables/table.html"
        fields = ("date", "buxfer_transaction_sum", "bank_transaction_sum")
        order_by = 'date'
