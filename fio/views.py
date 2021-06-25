from django.http import HttpResponseRedirect
from django_tables2 import SingleTableView

from . import fio_parser, models, tables, forms, buxfer_parser


class IndexView(SingleTableView):
    template_name = 'index.html'
    model = models.Transaction
    table_class = tables.TransactionTable

    def get_context_data(self, **kwargs):
        coontext = super().get_context_data()
        coontext["form"] = forms.LoadDataFromBankForm()
        return coontext

    def post(self, request, *args, **kwargs):
        bank_profile = models.BankProfile.objects.get(user=request.user)
        form = forms.LoadDataFromBankForm(request.POST)
        if form.is_valid():
            date_from = form.cleaned_data['date_from']
            date_to = form.cleaned_data['date_to']
            fio_parser.copy_transaction_from_buxfer(bank_profile.fio_bank_token, date_from, date_to)
        return HttpResponseRedirect("/")


class BuxferTransactionTableView(SingleTableView):
    template_name = 'buxfer_transaction_table.html'
    model = models.BuxferTransaction
    table_class = tables.TransactionTable

    def get_context_data(self, **kwargs):
        coontext = super().get_context_data()
        coontext["form"] = forms.LoadDataFromBuxferForm()
        return coontext

    def post(self, request, *args, **kwargs):
        bank_profile = models.BankProfile.objects.get(user=request.user)
        username = bank_profile.buxfer_username
        password = bank_profile.buxfer_password
        form = forms.LoadDataFromBankForm(request.POST)
        if form.is_valid():
            date_from = form.cleaned_data['date_from']
            date_to = form.cleaned_data['date_to']
            buxfer_parser.download_transaction_from_buxfer(username, password, date_from, date_to)
        return HttpResponseRedirect("/")
