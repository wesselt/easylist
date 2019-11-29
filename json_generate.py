import argparse
from decimal import Decimal
import json
import sys
from cgi import parse_qs

import bunq
import db
import guidhelper


bunq.set_log_level(0)


def process_account(row, user_id, account_id):
    result = []
    method = ("v1/user/{0}/monetary-account/{1}/payment?count=128"
              .format(user_id, account_id))
    payments = bunq.get(row, method)
    for v in [p["Payment"] for p in payments]:
        result.append({
            "amount": v["amount"]["value"],
            "currency": v["amount"]["currency"],
            "created": v["created"][:16],
            "type": v["type"],
            "sub_type": v["sub_type"],
            "description": v["description"],
            "from_iban": v["alias"]["iban"],
            "from_name": v["alias"]["display_name"],
            "to_iban": v["counterparty_alias"]["iban"],
            "to_name": v["counterparty_alias"]["display_name"]
        })
    return result 


def process_user(row, user_id):
    result = []
    method = 'v1/user/{0}/monetary-account'.format(user_id)
    for a in bunq.get(row, method):
        for k, v in a.items():
            result.extend(process_account(row, user_id, v["id"]))
    return result

def get_transactions(row):
    result = []
    users = bunq.get(row, 'v1/user')
    for u in users:
        for k, v in u.items():
            result += process_user(row, v['id'])
    return result


def error(message):
    return [json.dumps({"error": message}).encode()]


def application(env, start_response):
    start_response('200 OK', [
        ('Content-Type','text/json'),
        ('Content-Disposition', 'inline; filename="easylist.json"'),
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
        return [json.dumps(result).encode()]
    except Exception as e:
        return error(str(e))
