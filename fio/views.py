import datetime
import json

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db.models import Q, QuerySet, Avg, F, Window, Sum
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.views.generic import DetailView, UpdateView
from django.views.generic.edit import FormView
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


class BankTransactionsNotUploadedTableView(BankTransactionTableView):
    def get_queryset(self):
        queryset = super().get_queryset()
        queryset: QuerySet[models.Transaction]
        return queryset.filter(buxfertransaction__isnull=True).order_by("-transaction_date")


class BuxferTransactionTableView(SingleTableView):
    template_name = 'buxfer_transaction_table.html'
    model = models.BuxferTransaction
    table_class = tables.BuxferTransactionTable

    def get_context_data(self, **kwargs):
        coontext = super().get_context_data()
        coontext["form"] = forms.LoadDataFromBuxferForm()
        return coontext


class BuxferUnmatchedTransactionTableView(BuxferTransactionTableView):
    def get_queryset(self):
        queryset = super().get_queryset()
        return buxfer_parser.filter_unmatched_transactions(queryset)


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context["not_uploaded_count"] = models.Transaction.objects.filter(buxfertransaction__isnull=True).count()
        return context

    def form_valid(self, form):
        bank_profile = models.BankProfile.objects.get(user=self.request.user)
        form = forms.LoadDataFromBankForm(self.request.POST)
        if form.is_valid():
            date_from = form.cleaned_data['date_from']
            date_to = form.cleaned_data['date_to']
            fio_parser.copy_transaction_from_bank(bank_profile, date_from, date_to, self.request.user)
        return HttpResponseRedirect("/")


class BuxferUploadDataView(FormView):
    template_name = 'buxfer_upload_data.html'
    form_class = forms.UploadDataToBuxferForm
    success_url = '/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context["not_uploaded_count"] = models.Transaction.objects.filter(buxfertransaction__isnull=True).count()
        return context

    def form_valid(self, form):
        bank_profile = models.BankProfile.objects.get(user=self.request.user)
        form = forms.LoadDataFromBankForm(self.request.POST)
        if form.is_valid():
            date_from = form.cleaned_data['date_from']
            date_to = form.cleaned_data['date_to']
            buxfer_parser.send_bank_transactions_from_period_to_buxfer(date_from, date_to, bank_profile)
        return HttpResponseRedirect("/")


class BuxferTransactionDetailView(DetailView):
    template_name = 'buxfer_transaction_detail.html'
    model = models.BuxferTransaction

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        potential_bank_transactions = buxfer_parser.find_potential_bank_transaction(self.object)
        if potential_bank_transactions.count() == 0:
            potential_bank_transactions = models.Transaction.objects.filter(
                transaction_date=self.object.transaction_date)
        context["table"] = tables.TransactionTable(potential_bank_transactions)
        return context


class SendSingleTransactionToBuxferView(UpdateView):
    def post(self, request, *args, **kwargs):
        transaction_id = json.loads(request.body)["transaction_id"]
        tranaction = models.Transaction.objects.get(pk=transaction_id)
        bank_profile = models.BankProfile.objects.get(user=self.request.user)
        response = buxfer_parser.send_bank_transaction_to_buxfer(tranaction, bank_profile)
        return JsonResponse(response)


class BuxferUpdateSingleTransactionView(UpdateView):
    def post(self, request, *args, **kwargs):
        buxfer_transaction_id = json.loads(request.body)["transaction_id"]
        buxfer_tranaction = models.BuxferTransaction.objects.get(pk=buxfer_transaction_id)
        bank_profile = models.BankProfile.objects.get(user=self.request.user)
        response = buxfer_parser.update_bank_transaction_description(buxfer_tranaction, bank_profile)
        return JsonResponse(response)


class UploadAutoTaggingStringsView(FormView):
    form_class = forms.UploadAutoTaggingStringsForm
    template_name = 'upload_auto_tagging_strings.html'
    success_url = '/'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        auto_tagging_string_file: InMemoryUploadedFile = request.FILES['auto_tagging_string_file']
        if form.is_valid():
            auto_tagging_string_list = json.load(auto_tagging_string_file)
            for item in auto_tagging_string_list.items():
                auto_tagging_string_query = models.AutoTaggingString.objects.filter(tagging_string=item[0])
                if auto_tagging_string_query.count() == 1:
                    auto_tagging_string = auto_tagging_string_query.first()
                else:
                    auto_tagging_string = models.AutoTaggingString()
                    auto_tagging_string.tagging_string = item[0]
                auto_tagging_string.tag = item[1]
                auto_tagging_string.save()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class MatchTransactionsView(FormView):
    template_name = 'match_transactions.html'
    form_class = forms.MatchTransactionsForm
    success_url = '/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context["unmatched_transactions"] = buxfer_parser.filter_unmatched_transactions(
            models.BuxferTransaction.objects.all()).count()
        return context

    def form_valid(self, form):
        form = forms.MatchTransactionsForm(self.request.POST)
        if form.is_valid():
            date_from = form.cleaned_data['date_from']
            date_to = form.cleaned_data['date_to']
            unmatched_transactions = models.BuxferTransaction.objects.filter(
                Q(transaction_date__gt=date_from) & Q(transaction_date__lt=date_to))
            unmatched_transactions = buxfer_parser.filter_unmatched_transactions(unmatched_transactions)
            for buxfer_transaction in unmatched_transactions:
                potential_transaction = buxfer_parser.find_potential_bank_transaction(buxfer_transaction)
                if potential_transaction.count() == 1:
                    buxfer_transaction.bank_transaction = potential_transaction.first()
                    buxfer_transaction.save()
        return HttpResponseRedirect("/")


class AccountBalanceView(SingleTableView):
    template_name = 'account_balance.html'
    table_class = tables.AccountBalanceTable
    success_url = '/'

    def get_queryset(self):
        return models.AccountBalance.objects.filter(~Q(buxfer_transaction_sum=F("bank_transaction_sum")))

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context["form"] = forms.RecalculateAccountBalanceForm()
        return context

    def post(self, request, *args, **kwargs):
        bank_profile = models.BankProfile.objects.get(user=request.user)
        form = forms.RecalculateAccountBalanceForm(request.POST)
        if form.is_valid():
            date_from = form.cleaned_data['date_from']
            date_to = form.cleaned_data['date_to']
            models.AccountBalance.objects.all().delete()
            current_date = date_from
            while current_date <= date_to:
                account_balance = models.AccountBalance(date=current_date, account=bank_profile.main_bank_account)
                account_balance.calculate_balance()
                current_date += datetime.timedelta(days=1)
        return HttpResponseRedirect("/")


class AccountBalanceDetailView(DetailView):
    template_name = 'account_balance_detail.html'
    model = models.AccountBalance

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context["bank_transaction_table"] = tables.TransactionTable(data=self.object.get_bank_transactions())
        context["buxfer_transaction_table"] = tables.BuxferTransactionTable(data=self.object.get_buxfer_transactions())
        return context
