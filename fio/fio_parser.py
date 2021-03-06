import datetime
import decimal
import re
import time
import xml.etree.ElementTree as ET

import requests

from . import models

MAX_BATCH_LENGTH = 35
BANK_REQUEST_PAUSE = 30
COLUMN_NAMES_MAPPING = {
    "column_0": ("transaction_date", lambda x: datetime.datetime.fromisoformat(x).date()),
    "column_1": ("amount", lambda x: decimal.Decimal(x)),
    "column_2": ("contra_account", lambda x: x),
    "column_3": ("contra_account_bank_code", lambda x: x),
    "column_4": ("constant_symbol", lambda x: x),
    "column_5": ("variable_code", lambda x: x),
    "column_7": ("user_identification", lambda x: x),
    "column_8": ("bank_transaction_type", lambda x: x),
    "column_12": ("bank_name", lambda x: x),
    "column_14": ("currency", lambda x: x),
    "column_16": ("receiver_message", lambda x: x),
    "column_17": ("request_id", lambda x: int(x)),
    "column_22": ("bank_transaction_id", lambda x: int(x)),
    "column_25": ("comment", lambda x: x)
}


def get_url(token, url_type="periods", date_from=None, date_to=None):
    if not date_from:
        date_from = datetime.datetime.today().date() + datetime.timedelta(days=-30)
    if not date_to:
        date_to = datetime.datetime.today().date()
    return f"https://www.fio.cz/ib_api/rest/{url_type}/{token}/{date_from}/{date_to}/transactions.xml"


def process_response(bank_profile: models.BankProfile, text, user: models.User):
    root = ET.fromstring(text)
    date_regex = re.compile(r"\d{1,2}\.\d{1,2}\.\d{4}")

    for transaction in root[1]:
        transaction_record = models.Transaction()
        for column in transaction:
            if column.tag in COLUMN_NAMES_MAPPING:
                function = COLUMN_NAMES_MAPPING[column.tag][1]
                setattr(transaction_record, COLUMN_NAMES_MAPPING[column.tag][0], function(column.text))
        transaction_record.bank_transaction_date = transaction_record.transaction_date
        if transaction_record.description:
            date_regex_results = date_regex.findall(transaction_record.description)
            for result in date_regex_results:
                result: str
                result_split = result.split(".")
                transaction_record.transaction_date = datetime.datetime(int(result_split[2]), int(result_split[1]),
                                                                        int(result_split[0]))
        transaction_query = models.Transaction.objects.filter(
            bank_transaction_id=transaction_record.bank_transaction_id)
        if transaction_query.count() == 0:
            transaction_record.user = user
            transaction_record.bank_account = bank_profile.main_bank_account
            transaction_record.save()
        else:
            transaction_record = transaction_query.first()
        buxfer_transaction_query = models.BuxferTransaction.objects.filter(
            buxfer_bank_transaction_id=transaction_record.bank_transaction_id)
        if buxfer_transaction_query.count() == 1:
            buxfer_transaction = buxfer_transaction_query.first()
            buxfer_transaction.bank_transaction = transaction_record
            buxfer_transaction.save()


def copy_transaction_from_bank(bank_profile: models.BankProfile, date_from: datetime, date_to: datetime,
                               user: models.User):
    token = bank_profile.fio_bank_token
    if (date_to - date_from).days < MAX_BATCH_LENGTH:
        url = get_url(token, date_from=date_from, date_to=date_to)
        response = requests.get(url)
        if not response.ok:
            raise ValueError("Error getting data from bank.")
        process_response(bank_profile, response.text, user)
    else:
        actual_date_from = date_to + datetime.timedelta(days=-30)
        actual_date_to = date_to
        while actual_date_from > date_from:
            url = get_url(token, date_from=actual_date_from, date_to=actual_date_to)
            response = requests.get(url)
            if not response.ok:
                print(response.text)
                raise ValueError("Error getting data from bank.")
            process_response(bank_profile, response.text, user)
            actual_date_to = actual_date_from + datetime.timedelta(days=-1)
            actual_date_from += datetime.timedelta(days=-60)
            time.sleep(BANK_REQUEST_PAUSE)
