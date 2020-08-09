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


class Generate:
    def __init__(self, env, start_response):
        self.env = env
        self.start_response = start_response
        self.row = None
        self.oldest_payment_dt = None
        self.last_payment = None
        self.end_time = None
        self.time_limit = 25  # Google sheet IMPORTDATA times out after 25s


    def time_exceeded(self):
        if self.end_time < time.time():
            print("*** Time exceeded")
            return True


    def age_exceeded(self):
        if not self.last_payment:
            return False
        if self.oldest_payment_dt <= self.last_payment["created"][:10]:
            return False
        print("*** Age exceeded")
        return True


    def payment_to_line(self, payment):
        return '{0},{1},{2},{3},{4},"{5}",{6},{7},{8},{9}\n'.format(
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
        ).encode()
        return [f"Error: {message}\n".encode()]


    def process_payments(self, payments):
        for v in [p["Payment"] for p in payments]:
            self.last_payment = v
            if self.age_exceeded():
                return
            yield self.payment_to_line(v)


    def process_account(self, user_id, account_id):
        method = ("v1/user/{0}/monetary-account/{1}/payment?count=200"
                  .format(user_id, account_id))
        payments = bunq.get(self.row, method)
        yield from self.process_payments(payments)
        while bunq.has_previous():
            if self.time_exceeded() or self.age_exceeded():
                return
            payments = bunq.previous(self.row)
            yield from self.process_payments(payments)


    def process_user(self, user_id):
        method = 'v1/user/{0}/monetary-account'.format(user_id)
        for a in bunq.get(self.row, method):
            if self.time_exceeded() or self.age_exceeded():
                return
            for k, v in a.items():
                yield from self.process_account(user_id, v["id"])


    def get_payments(self):
        self.last_payment = None
        self.end_time = time.time() + self.time_limit
        dt = datetime.datetime.now() - datetime.timedelta(weeks=53)
        self.oldest_payment_dt = dt.strftime("%Y-%m-%d")
        yield ("amount,currency,created,type,sub_type,description," +
                  "from_iban,from_name,to_iban,to_name\n").encode()
        users = bunq.get(self.row, 'v1/user')
        for u in users:
            if self.time_exceeded():
                return
            for k, v in u.items():
                #result += f"{k} {v['display_name']} {v['id']}"
                yield from self.process_user(v['id'])


    def error(self, message):
        print("Error: " + message)
        return [f"Error: {message}\n".encode()]


    def run(self):
        self.start_response('200 OK', [
            ('Content-Type', 'text/csv'),
            ('Content-Disposition', 'inline; filename="easylist.csv"'),
        ])
        d = parse_qs(self.env["QUERY_STRING"])
        if "guid" not in d:
            return self.error("Parameter guid required")
        self.guid = d["guid"][0]
        if not guidhelper.validate_uuid4(self.guid):
            return self.error("Parameter guid must be a valid guid")
        self.row = db.get_row(self.guid)
        if not self.row:
            return self.error(f"Unknown guid {self.guid}")
        try:
            return self.get_payments()
        except Exception as e:
            print("Error: " + str(e))
            return self.error(str(e))


def application(env, start_response):
    #start_response('200 OK', [
    #    ('Content-Type', 'text/csv'),
    #    ('Content-Disposition', 'inline; filename="easylist.csv"'),
    #])
    #return [b"Gloep"]
    generate = Generate(env, start_response)
    return generate.run()
