from django.http import HttpResponseRedirect, JsonResponse
from django.views.generic.edit import FormView
from django.views.generic import DetailView, UpdateView
from django_tables2 import SingleTableView
import json

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
            fio_parser.copy_transaction_from_bank(bank_profile.fio_bank_token, date_from, date_to)
        return HttpResponseRedirect("/")


class BankTransactionDetailView(DetailView):
    template_name = 'bank_transaction_detail.html'
    model = models.Transaction

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["buxfer_preview"] = json.dumps(buxfer_parser.convert_transaction_for_buxfer(self.object), indent=4)
        return context


class BankTransactionTableView(SingleTableView):
    template_name = 'bank_transaction_table.html'
    model = models.Transaction
    table_class = tables.TransactionTable


class BuxferTransactionTableView(SingleTableView):
    template_name = 'buxfer_transaction_table.html'
    model = models.BuxferTransaction
    table_class = tables.BuxferTransactionTable

    def get_context_data(self, **kwargs):
        coontext = super().get_context_data()
        coontext["form"] = forms.LoadDataFromBuxferForm()
        return coontext


class BuxferLoadDataView(FormView):
    template_name = 'buxfer_load_data.html'
    form_class = forms.LoadDataFromBuxferForm
    success_url = '/'

    def form_valid(self, form):
        bank_profile = models.BankProfile.objects.get(user=self.request.user)
        form = forms.LoadDataFromBankForm(self.request.POST)
        if form.is_valid():
            date_from = form.cleaned_data['date_from']
            date_to = form.cleaned_data['date_to']
            buxfer_parser.download_transaction_from_buxfer(bank_profile, self.request.user, date_from, date_to)
        return HttpResponseRedirect("/")


class BankLoadDataView(FormView):
    template_name = 'bank_load_data.html'
    form_class = forms.LoadDataFromBankForm
    success_url = '/'

    def form_valid(self, form):
        bank_profile = models.BankProfile.objects.get(user=self.request.user)
        form = forms.LoadDataFromBankForm(self.request.POST)
        if form.is_valid():
            date_from = form.cleaned_data['date_from']
            date_to = form.cleaned_data['date_to']
            fio_parser.copy_transaction_from_bank(bank_profile, date_from, date_to, self.request.user)
        return HttpResponseRedirect("/")


class SendSingleTransactionToBuxferView(UpdateView):
    def post(self, request, *args, **kwargs):
        transaction_id = json.loads(request.body)["transaction_id"]
        tranaction = models.Transaction.objects.get(pk=transaction_id)
        bank_profile = models.BankProfile.objects.get(user=self.request.user)
        response = buxfer_parser.send_bank_transaction_to_buxfer(tranaction, bank_profile)
        return JsonResponse(response)
