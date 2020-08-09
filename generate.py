import argparse
from decimal import Decimal
import json
import sys
from cgi import parse_qs
from pprint import pprint

import bunq
import db
import guidhelper


bunq.set_log_level(0)


def payment_to_line(payment):
    return "{0},{1},{2},{3},{4},{5},{6},{7},{8},{9}".format(
        payment["amount"]["value"],
        payment["amount"]["currency"],
        payment["created"][:16],
        payment["type"],
        payment["sub_type"],
        payment["description"],
        payment["alias"]["iban"],
        payment["alias"]["display_name"],
        payment["counterparty_alias"]["iban"],
        payment["counterparty_alias"]["display_name"]
    )


def process_payments(payments):
    result = []
    for v in [p["Payment"] for p in payments]:
        result.append(payment_to_line(v))
    return result


def process_account(row, user_id, account_id):
    method = ("v1/user/{0}/monetary-account/{1}/payment?count=200"
              .format(user_id, account_id))
    payments = bunq.get(row, method)
    result = process_payments(payments)
    while bunq.has_previous():
        payments = bunq.previous(row)
        pprint(result)
        result.extend(process_payments(payments))
    return "\n".join(result)


def process_user(row, user_id):
    result = ""
    method = 'v1/user/{0}/monetary-account'.format(user_id)
    for a in bunq.get(row, method):
        for k, v in a.items():
            result += process_account(row, user_id, v["id"])
    return result

def get_transactions(row):
    result = ("amount,currency,created,type,sub_type,description," +
              "from,from_name,to_iban,to_name\n")
    users = bunq.get(row, 'v1/user')
    for u in users:
        for k, v in u.items():
            #result += f"{k} {v['display_name']} {v['id']}"
            result += process_user(row, v['id'])
    return result


def error(message):
    return f"Error: {message}\n"


def application(env, start_response):
    start_response('200 OK', [
        ('Content-Type', 'text/csv'),
        ('Content-Disposition', 'inline; filename="easylist.csv"'),
    ])
    d = parse_qs(env["QUERY_STRING"])
    if "guid" not in d:
        return error("Parameter guid required")
    guid = d["guid"][0]
    if guidhelper.validate_uuid4(guid):
        return error("Parameter guid must be a valid guid")
    row = db.get_row(guid)
    if not row:
        return error(f"Unknown guid {guid}")
    try:
        result = get_transactions(row)
        db.put_row(row)
        return [result.encode()]
    except Exception as e:
        return [error(str(e)).encode()]
