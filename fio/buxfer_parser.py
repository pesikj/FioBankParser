import datetime
import decimal
import json
import math
import re
import time

import requests
from django.db import IntegrityError
from django.db.models import Q, QuerySet
from django.utils import timezone
from django.utils.timezone import make_aware
from requests.models import Response

from . import models
from .fio_parser import BANK_REQUEST_PAUSE

BANK_REQUEST_PAUSE = 10

MAX_BATCH_LENGTH = 35
COLUMN_NAMES_MAPPING = {
    "id": ("buxfer_id", lambda x: int(x)),
    "description": ("description", lambda x: x),
    "date": ("transaction_date", lambda x: datetime.datetime.fromisoformat(x).date()),
    "type": ("transaction_type", lambda x: x),
    "amount": ("amount", lambda x: decimal.Decimal(x)),
    "expenseAmount": ("expense_amount", lambda x: decimal.Decimal(x)),
    "accountId": ("buxfer_account_id", lambda x: int(x)),
    "accountName": ("buxfer_account_name", lambda x: x),
    "tags": ("tags", lambda x: x),
    "tagNames": ("tag_names", lambda x: x),
    "status": ("status", lambda x: x),
    "isFutureDated": ("is_future_dated", lambda x: x),
    "isPending": ("is_pending", lambda x: int(x)),
}

TRANSACTION_TYPES_MAPPING = {
    "Poplatek - platební karta": "expense",
    "Platba v jiné měně": "expense",
    "Inkaso": "expense",
    "Platba v hotovosti": "expense",
    "Platba převodem uvnitř banky": "expense",
    "Platba kartou - příjem": "refund",
    "Dobití kreditu mobilního telefonu": "expense",
    "Příjem v hotovosti": "income",
    "Platba kartou": "expense",
    "Vklad pokladnou": "income",
    "Bezhotovostní příjem": "income",
    "Příjem převodem uvnitř banky": "income",
    "Bezhotovostní platba": "expense",
    "Poplatek": "expense",
    "Okamžitá odchozí platba": "expense",
    "Okamžitá příchozí platba": "income"
}


def login_to_buxfer(bank_profile: models.BankProfile):
    if not bank_profile.buxfer_token or not bank_profile.buxfer_token_created_on or \
            bank_profile.buxfer_token_created_on < make_aware(datetime.datetime.now() + datetime.timedelta(days=-1),
                                                              timezone.get_default_timezone()):
        base = "https://www.buxfer.com/api"
        url = base + "/login?userid=" + bank_profile.buxfer_username + "&password=" + bank_profile.buxfer_password
        response: Response = requests.get(url)
        response_json = json.loads(response.text)
        token = response_json["response"]["token"]
        bank_profile.buxfer_token = token
        bank_profile.buxfer_token_created_on = datetime.datetime.now()
        bank_profile.save()
    return bank_profile.buxfer_token


def filter_unmatched_transactions(queryset: QuerySet[models.BuxferTransaction]) -> QuerySet[models.BuxferTransaction]:
    return queryset.filter(
        Q(bank_transaction__isnull=True) & ~Q(from_account__cash=True) & ~Q(to_account__cash=True) & ~Q(
            account__cash=True))


def find_potential_bank_transaction(transaction: models.BuxferTransaction) -> QuerySet[models.Transaction]:
    if transaction.transaction_type == "expense" and transaction.from_account and transaction.from_account.cash \
            or transaction.transaction_type == "income" and transaction.to_account and transaction.to_account.cash:
        return None
    bank_transaction_query = models.Transaction.objects.filter(
        Q(transaction_date=transaction.transaction_date) & Q(
            buxfertransaction__isnull=True) & Q())
    if transaction.transaction_type == "expense":
        bank_transaction_query = bank_transaction_query.filter(amount=-transaction.amount)
    elif transaction.transaction_type == "income":
        bank_transaction_query = bank_transaction_query.filter(amount=transaction.amount)
    else:
        bank_transaction_query = bank_transaction_query\
            .filter(Q(amount=transaction.amount) | Q(amount=-transaction.amount))
    return bank_transaction_query


def download_batch_from_buxfer(start_date: datetime, end_date: datetime, token: str, user: models.User):
    dict_start_date = {"startDate": start_date, "endDate": end_date}
    url = "https://www.buxfer.com/api/transactions?token=" + token
    response: Response = requests.post(url, dict_start_date)
    response_json = json.loads(response.text)
    transaction_count = int(response_json["response"]["numTransactions"])
    pages = math.ceil(transaction_count / 25) + 1
    for currPage in range(pages, 0, -1):
        time.sleep(BANK_REQUEST_PAUSE)
        dict_page = dict_start_date
        dict_page["page"] = currPage
        response: Response = requests.post(url, dict_page)
        response_transactions_json = json.loads(response.text)
        for transaction_dict in response_transactions_json["response"]["transactions"]:
            transaction_record_query = models.BuxferTransaction.objects.filter(buxfer_id=int(transaction_dict["id"]))
            if transaction_record_query.count() == 1:
                transaction_record = transaction_record_query.first()
            else:
                transaction_record = models.BuxferTransaction()
            transaction_record.user = user
            transaction_record.raw_data = transaction_dict
            for column_name, value in transaction_dict.items():
                if column_name in COLUMN_NAMES_MAPPING:
                    function = COLUMN_NAMES_MAPPING[column_name][1]
                    setattr(transaction_record, COLUMN_NAMES_MAPPING[column_name][0], function(value))
                if column_name == "fromAccount":
                    bank_accounts = models.BankAccount.objects.filter(buxfer_account_id=value["id"])
                    if bank_accounts.count() == 1:
                        transaction_record.from_account = bank_accounts.first()
                elif column_name == "toAccount":
                    bank_accounts = models.BankAccount.objects.filter(buxfer_account_id=value["id"])
                    if bank_accounts.count() == 1:
                        transaction_record.to_account = bank_accounts.first()
                elif column_name == "description":
                    regex = re.compile(r"Bank ID: \d{9,12}")
                    results = regex.findall(value)
                    if len(results) > 0:
                        res = results[-1]
                        res = res.replace("Bank ID: ", "")
                        transaction_record.buxfer_bank_transaction_id = int(res)
                        try:
                            bank_transaction = models.Transaction.objects.filter(bank_transaction_id=int(res)).first()
                            transaction_record.bank_transaction = bank_transaction
                        except models.Transaction.DoesNotExist as err:
                            print(err)
            if transaction_record.buxfer_account_id:
                transaction_record.account = models.BankAccount.objects.filter(
                    buxfer_account_id=transaction_record.buxfer_account_id).first()
            if not transaction_record.bank_transaction:
                bank_transaction_query = find_potential_bank_transaction(transaction_record)
                if bank_transaction_query.count() > 0:
                    transaction_record.bank_transaction = bank_transaction_query.first()
            try:
                transaction_record.save()
            except IntegrityError as err:
                print(err)


def download_transaction_from_buxfer(bank_profile: models.BankProfile, user: models.User, date_from: datetime,
                                     date_to: datetime):
    token = login_to_buxfer(bank_profile)
    if (date_to - date_from).days < MAX_BATCH_LENGTH:
        download_batch_from_buxfer(date_from, date_to, token, user)
    else:
        actual_date_from = date_to + datetime.timedelta(days=-30)
        actual_date_to = date_to
        while actual_date_from > date_from:
            download_batch_from_buxfer(actual_date_from, actual_date_to, token, user)
            actual_date_to = actual_date_from + datetime.timedelta(days=-1)
            actual_date_from += datetime.timedelta(days=-60)


def convert_transaction_for_buxfer(transaction: models.Transaction) -> dict:
    dict_transaction_buxfer = {"description": f"{transaction.description}; Bank ID: {transaction.bank_transaction_id}"}
    transaction_type = TRANSACTION_TYPES_MAPPING[transaction.bank_transaction_type]
    if transaction.from_account:
        dict_transaction_buxfer["fromAccountId"] = transaction.from_account.buxfer_account_id
    if transaction.to_account:
        dict_transaction_buxfer["toAccountId"] = transaction.to_account.buxfer_account_id
        if transaction.to_account.account_number == "Cash":
            transaction_type = "transfer"
    if transaction.from_account and transaction.to_account:
        dict_transaction_buxfer["type"] = "transfer"
    else:
        dict_transaction_buxfer["type"] = transaction_type
    dict_transaction_buxfer["amount"] = "%8.2f" % abs(transaction.amount)
    dict_transaction_buxfer["date"] = str(transaction.transaction_date)
    if transaction_type == "transfer":
        tags = "Money Transfer"
        dict_transaction_buxfer["tags"] = tags
    auto_tagging_string = models.AutoTaggingString.objects.all()
    for auto_tagging_string in auto_tagging_string:
        if transaction.comment and auto_tagging_string.tagging_string.lower() in transaction.comment.lower():
            dict_transaction_buxfer["tags"] = auto_tagging_string.tag
            break
        if transaction.user_identification \
                and auto_tagging_string.tagging_string.lower() in transaction.user_identification.lower():
            dict_transaction_buxfer["tags"] = auto_tagging_string.tag
            break
        if transaction.receiver_message \
                and auto_tagging_string.tagging_string.lower() in transaction.receiver_message.lower():
            dict_transaction_buxfer["tags"] = auto_tagging_string.tag
            break
    return dict_transaction_buxfer


def send_bank_transaction_to_buxfer(transaction: models.Transaction, bank_profile: models.BankProfile, token=None):
    dict_transaction_buxfer = convert_transaction_for_buxfer(transaction)
    if not token:
        token = login_to_buxfer(bank_profile)
    url = "https://www.buxfer.com/api/add_transaction?token=" + token
    response: Response = requests.post(url, dict_transaction_buxfer)
    response_json = json.loads(response.text)
    if response.status_code == 200:
        transaction.buxfer_response = response_json
        transaction.save()
    return response_json


def update_bank_transaction_description(buxfer_transaction: models.BuxferTransaction, bank_profile: models.BankProfile,
                                        token=None):
    dict_transaction_buxfer = {"id": buxfer_transaction.buxfer_id, "description": buxfer_transaction.updated_description}
    if not token:
        token = login_to_buxfer(bank_profile)
    url = "https://www.buxfer.com/api/transaction_edit?token=" + token
    response: Response = requests.post(url, dict_transaction_buxfer)
    response_json = json.loads(response.text)
    if response.status_code == 200:
        new_description = response_json["response"]["description"]
        buxfer_transaction.description = new_description
        buxfer_transaction.buxfer_update_response = response_json
        buxfer_transaction.save()
    return response_json


def send_bank_transactions_from_period_to_buxfer(date_from: datetime.datetime, date_to: datetime.datetime,
                                                 bank_profile: models.BankProfile):
    transaction_list = models.Transaction.objects.filter(Q(transaction_date__gte=date_from)
                                                         & Q(transaction_date__lte=date_to)
                                                         & Q(buxfertransaction__isnull=True)
                                                         & Q(buxfer_response__isnull=True))
    token = login_to_buxfer(bank_profile)
    for transaction in transaction_list:
        transaction: models.Transaction
        send_bank_transaction_to_buxfer(transaction, bank_profile, token)
        time.sleep(BANK_REQUEST_PAUSE)
