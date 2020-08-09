import argparse
from decimal import Decimal
import json
import sys
import datetime
import time
from cgi import parse_qs
from pprint import pprint

import bunq
import db
import guidhelper


bunq.set_log_level(0)


oldest_payment_dt = None
last_payment = None
end_time = None
time_limit = 25  # Google sheet IMPORTDATA times out after 25 seconds


def time_exceeded():
    if end_time < time.time():
        print("*** Time exceeded")
        return True


def age_exceeded():
    if not last_payment:
        return False
    return last_payment["created"][:10] < oldest_payment_dt 


def payment_to_line(payment):
    return '{0},{1},{2},{3},{4},"{5}",{6},{7},{8},{9}'.format(
        payment["amount"]["value"],
        payment["amount"]["currency"],
        payment["created"][:16],
        payment["type"],
        payment["sub_type"],
        payment["description"].replace('"', '\\"').rstrip(),
        payment["alias"]["iban"],
        payment["alias"]["display_name"],
        payment["counterparty_alias"]["iban"],
        payment["counterparty_alias"]["display_name"]
    )


def process_payments(payments):
    global last_payment
    for v in [p["Payment"] for p in payments]:
        last_payment = v
        if age_exceeded():
            return
        yield payment_to_line(v)


def process_account(row, user_id, account_id):
    method = ("v1/user/{0}/monetary-account/{1}/payment?count=200"
              .format(user_id, account_id))
    payments = bunq.get(row, method)
    yield from process_payments(payments)
    while bunq.has_previous():
        if time_exceeded() or age_exceeded():
            return
        payments = bunq.previous(row)
        yield from process_payments(payments)


def process_user(row, user_id):
    method = 'v1/user/{0}/monetary-account'.format(user_id)
    for a in bunq.get(row, method):
        if time_exceeded() or age_exceeded():
            return
        for k, v in a.items():
            yield from process_account(row, user_id, v["id"])


def get_transactions(row):
    global end_time, oldest_payment_dt, last_payment
    last_payment = None
    end_time = time.time() + time_limit
    dt = datetime.datetime.now() - datetime.timedelta(weeks=53)
    oldest_payment_dt = dt.strftime("%Y-%m-%d")
    yield ("amount,currency,created,type,sub_type,description," +
              "from,from_name,to_iban,to_name")
    users = bunq.get(row, 'v1/user')
    for u in users:
        if time_exceeded():
            return
        for k, v in u.items():
            #result += f"{k} {v['display_name']} {v['id']}"
            yield from process_user(row, v['id'])


def error(message):
    return [f"Error: {message}\n".encode()]


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
        result = "\n".join(get_transactions(row))
        db.put_row(row)
        return result.encode()
    except Exception as e:
        return error(str(e))
