from decimal import Decimal
import json
import sys
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
                    "user_id": user_id,
                    "account_id": a["id"],
                    "description": a["description"],
                    "iban": al["value"],
                    "value": a["balance"]["value"],
                    "currency": a["balance"]["currency"],
                    "name": al["name"]
                })
    return accounts


def collect_accounts(row):
    accounts = []
    for u in bunq.get(row, 'v1/user'):
        for k, v in u.items():
            accounts.extend(collect_user_accounts(row, v['id']))
    return accounts


def find_account(accounts, name):
    for a in accounts:
        if (name.casefold() == a["description"].casefold() or
                name.casefold() == a["iban"].casefold()):
            return a


def transfer(row, source_name, target_name, amount, description):
    accounts = collect_accounts(row)
    source = find_account(accounts, source_name)
    if not source:
        return {"error": f"No account matches source {source_name}"}
    target = find_account(accounts, target_name)
    if not target:
        return {"error": f"No account matches target {target_name}"}

    # Move balance to target account
    method = (f"v1/user/{source['user_id']}/monetary-account/" +
              f"{source['account_id']}/payment")
    data = {
        "amount": {
            "value": str(amount),
            "currency": source["currency"]
        },
        "counterparty_alias": {
            "type": "IBAN",
            "value": target["iban"],
            "name": target["name"]
        },
        "description": description
    }
    bunq.post(row, method, data)
    return {
        "success": "success",
        "message": f"Transferred {amount} {source['currency']} " +
          f"from {source['iban']} to {target['iban']}"
    }


def main(d, guid, row, env, start_response):
    start_response('200 OK', [
        ('Content-Type','text/json'),
    ])
    if "source" not in d:
        return {"error": "Parameter source must contain a bunq IBAN"}
    source = d["source"][0]
    if "target" not in d:
        return {"error": "Parameter target must contain a bunq IBAN"}
    target = d["target"][0]
    if "amount" not in d:
        return {"error": "Parameter amount missing"}
    try:
        amount = Decimal(d["amount"][0])
    except:
        return {"error": "Parameter amount is not a number"}
    if amount <= 0:
        return {"error": "Parameter amount is not positive"}
    if "description" not in d:
        description = "Easylist account transfer"
    else:
        description = d["description"][0]    
    return transfer(row, source, target, amount, description)
