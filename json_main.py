import json
from cgi import parse_qs
import traceback
import sys

import db
import guidhelper
import json_balance
import json_flush
import json_transactions


def error(start_response, message):
    start_response('200 OK', [
        ('Content-Type','text/json'),
    ])
    return [json.dumps({"error": message}).encode()]


# Return a string on error, or any other object for success
def call_main(d, guid, row, env, start_response):
    if "action" in d:
        action = d["action"][0]
        if action == "flush":
            return json_flush.main(d, guid, row, env, start_response)
        elif action == "balance":
            return json_balance.main(d, guid, row, env, start_response)
        return f"Unknown action {action}"
    # Return transactions by default
    return json_transactions.main(d, guid, row, env, start_response)


def application(env, start_response):
    d = parse_qs(env["QUERY_STRING"])
    if "guid" not in d:
        return error(start_response, "Parameter guid required")
    guid = d["guid"][0]
    if guidhelper.validate_uuid4(guid):
        return error(start_reponse, "Parameter guid must be a valid guid")
    row = db.get_row(guid)
    if not row:
        return error(start_response, f"Unknown guid {guid}")
    try:
        result = call_main(d, guid, row, env, start_response)
        if isinstance(result, str):
            return error(start_response, result)
        return [json.dumps(result, indent=4).encode()]
    except:
        exc_type, exc_value, exc_tb = sys.exc_info()
        start_response('200 OK', [
            ('Content-Type','text/json'),
        ])
        return [json.dumps({
            "error": traceback.format_exception_only(
                        exc_type, exc_value)[0].strip(),
            "stack": traceback.format_tb(exc_tb)
        }, indent=4).encode()]
