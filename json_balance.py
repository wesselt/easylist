from decimal import Decimal
import json
from cgi import parse_qs

import bunq


bunq.set_log_level(0)


def collect_user_accounts(row, user_id):
    accounts = []
    method = f"v1/user/{user_id}/monetary-account"
    for e in bunq.get(row, method):
        account_type = next(iter(e))
        a = e[account_type]
        for al in a["alias"]:
            if al["type"] == "IBAN":
                accounts.append({
                    #"user_id": user_id,
                    #"account_id": a["id"],
                    "description": a["description"],
                    "iban": al["value"],
                    "value": a["balance"]["value"],
                    "currency": a["balance"]["currency"],
                    #"name": al["name"]
                })
    return accounts


def collect_accounts(row):
    accounts = []
    for u in bunq.get(row, 'v1/user'):
        for k, v in u.items():
            accounts.extend(collect_user_accounts(row, v['id']))
    return accounts


def main(d, guid, row, env, start_response):
    start_response('200 OK', [
        ('Content-Type','text/json'),
    ])
    return collect_accounts(row)
