import datetime
import decimal
import time
import xml.etree.ElementTree as ET

import requests
from django.db import IntegrityError

from . import models

MAX_BATCH_LENGTH = 35
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

    for transaction in root[1]:
        tranaction_record = models.Transaction()
        for column in transaction:
            if column.tag in COLUMN_NAMES_MAPPING:
                function = COLUMN_NAMES_MAPPING[column.tag][1]
                setattr(tranaction_record, COLUMN_NAMES_MAPPING[column.tag][0], function(column.text))
        try:
            tranaction_record.user = user
            tranaction_record.bank_account = bank_profile.main_bank_account
            tranaction_record.save()
        except IntegrityError as err:
            print(err)


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
            time.sleep(60)
