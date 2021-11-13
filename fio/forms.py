from django import forms
import datetime


def get_initial_dates():
    date_from = datetime.datetime.now() - datetime.timedelta(days=30)
    date_to = datetime.date.today()
    return date_from.date(), date_to


class LoadDataFromBankForm(forms.Form):
    date_from = forms.DateField(initial=get_initial_dates()[0])
    date_to = forms.DateField(initial=get_initial_dates()[1])


class UploadDataToBuxferForm(forms.Form):
    date_from = forms.DateField(initial=get_initial_dates()[0])
    date_to = forms.DateField(initial=get_initial_dates()[1])


class LoadDataFromBuxferForm(forms.Form):
    date_from = forms.DateField(initial=get_initial_dates()[0])
    date_to = forms.DateField(initial=get_initial_dates()[1])


class UploadAutoTaggingStringsForm(forms.Form):
    auto_tagging_string_file = forms.FileField()


class MatchTransactionsForm(forms.Form):
    date_from = forms.DateField(initial=get_initial_dates()[0])
    date_to = forms.DateField(initial=get_initial_dates()[1])


class RecalculateAccountBalanceForm(forms.Form):
    date_from = forms.DateField(initial="2014-04-01")
    date_to = forms.DateField(initial="2015-01-01")
