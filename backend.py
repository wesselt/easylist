import json
import requests
import sys
import uuid
from cgi import parse_qs

import db
import settings


def error(message):
    return [json.dumps({"error": message}).encode()]


def validate_uuid4(uuid_string):
    """
    Validate that a UUID string is in
    fact a valid uuid4.
    Happily, the uuid module does the actual
    checking for us.
    It is vital that the 'version' kwarg be passed
    to the UUID() call, otherwise any 32-character
    hex string is considered valid.
    """
    try:
        val = uuid.UUID(uuid_string, version=4)
    except ValueError:
        # If it's a value error, then the string 
        # is not a valid hex code for a UUID.
        return False

    # If the uuid_string is a valid hex code, 
    # but an invalid uuid4,
    # the UUID.__init__ will convert it to a 
    # valid uuid4. This is bad for validation purposes.
    return val.hex == uuid_string


def application(env, start_response):
    start_response('200 OK', [('Content-Type','text/html')])
    d = parse_qs(env["QUERY_STRING"])
    if "get_guid" in d:
        guid = str(uuid.uuid4())
        return [json.dumps({"new_guid": guid}).encode()]
    if "guid" not in d:
        return error("Parameter guid required")
    guid = d["guid"][0]
    if validate_uuid4(guid):
        return error("Parameter guid must be a valid guid")
    code = d["code"][0] if "code" in d else ""
    row = db.get_row(guid)
    if not row:
        row = {"guid": guid}
        if code:
            row["code"] = code
        db.put_row(row)
    if not row.get("bearer"):
        if not code:
            return error("Parameter code required for guid without bearer")
        url = "https://api.oauth.bunq.com/v1/token"
        response = requests.post(url, params={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "https://easylist.aule.net/",
            "client_id": "88ad9f89f0081f7d17a9552a7ff8403b48882a521dcd5a7d7229aab16e721386",
            "client_secret": settings.get_client_secret()
        }).json()
        if "error" in response:
            return [json.dumps(response).encode()]
        if "access_token" not in response:
            return [json.dumps({"error": "No access_token returned", 
                                "raw_reply": response}).encode()]
        row["bearer"] = response["access_token"]
        db.put_row(row)
    return [json.dumps({"success": "success"}).encode()]
