from decimal import Decimal
import json
from cgi import parse_qs

import bunq


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


def main(d, guid, row, env, start_response):
    start_response('200 OK', [
        ('Content-Type','text/json'),
        ('Content-Disposition', 'inline; filename="easylist.json"'),
    ])
    return get_transactions(row)
