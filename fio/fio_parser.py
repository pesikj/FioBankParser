import requests
import xml.etree.ElementTree as ET
import decimal
import datetime

from django.db import IntegrityError

from . import models


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


def copy_transaction_from_buxfer(token, date_from=None, date_to=None):
    url = get_url(token, date_from=date_from, date_to=date_to)
    response = requests.get(url)

    if not response.ok:
        raise ValueError("Error getting data from bank.")
    root = ET.fromstring(response.text)

    for transaction in root[1]:
        tranaction_record = models.Transaction()
        for column in transaction:
            if column.tag in COLUMN_NAMES_MAPPING:
                function = COLUMN_NAMES_MAPPING[column.tag][1]
                setattr(tranaction_record, COLUMN_NAMES_MAPPING[column.tag][0], function(column.text))
        try:
            tranaction_record.save()
        except IntegrityError as err:
            print(err)

