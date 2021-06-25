import datetime
import decimal
import json
import math
import re
from django.core.exceptions import ObjectDoesNotExist

import requests
from django.db import IntegrityError
from requests.models import Response

from . import models

COLUMN_NAMES_MAPPING = {
    "id": ("buxfer_id", lambda x: int(x)),
    "description": ("description", lambda x: x),
    "date": ("transaction_date", lambda x: datetime.datetime.fromisoformat(x).date()),
    "type": ("transaction_type", lambda x: x),
    "amount": ("amount", lambda x: decimal.Decimal(x)),
    "expenseAmount": ("expense_amount", lambda x: decimal.Decimal(x)),
    "accountId": ("account_id", lambda x: int(x)),
    "accountName": ("account_name", lambda x: x),
    "tags": ("tags", lambda x: x),
    "tagNames": ("tag_names", lambda x: x),
    "status": ("status", lambda x: x),
    "isFutureDated": ("is_future_dated", lambda x: x),
    "isPending": ("is_pending", lambda x: int(x)),
}


def login_to_buxfer(username, password):
    base = "https://www.buxfer.com/api"
    url = base + "/login?userid=" + username + "&password=" + password
    response: Response = requests.get(url)
    response_json = json.loads(response.text)
    token = response_json["response"]["token"]
    return token


def download_transaction_from_buxfer(username, password, start_date, end_date):
    token = login_to_buxfer(username, password)
    dict_start_date = {"startDate": start_date, "endDate": end_date}
    url = "https://www.buxfer.com/api/transactions?token=" + token
    response: Response = requests.post(url, dict_start_date)
    response_json = json.loads(response.text)
    transaction_count = int(response_json["response"]["numTransactions"])
    pages = math.ceil(transaction_count / 25) + 1
    for currPage in range(pages, 0, -1):
        dict_page = dict_start_date
        dict_page["page"] = currPage
        response: Response = requests.post(url, dict_page)
        response_transactions_json = json.loads(response.text)
        for transaction_dict in response_transactions_json["response"]["transactions"]:
            transaction_record = models.BuxferTransaction()
            for column_name, value in transaction_dict.items():
                if column_name in COLUMN_NAMES_MAPPING:
                    function = COLUMN_NAMES_MAPPING[column_name][1]
                    setattr(transaction_record, COLUMN_NAMES_MAPPING[column_name][0], function(value))
                if column_name == "description":
                    regex = re.compile(r"Bank ID: \d{9,12}")
                    results = regex.findall(value)
                    for res in results:
                        res = res.replace("Bank ID: ", "")
                        try:
                            bank_transaction = models.Transaction.objects.get(pk=int(res))
                            transaction_record.bank_transaction = bank_transaction
                        except models.Transaction.DoesNotExist as err:
                            print(err)
                        break
                try:
                    transaction_record.save()
                except IntegrityError as err:
                    print(err)
