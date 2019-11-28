import json
import requests
import sys
from cgi import parse_qs

import bunq
import db
import guidhelper
import settings


def error(message):
    return [json.dumps({"error": message}).encode()]


def prefetch_session(row):
    print("Prefetching session {row}")
    bunq.get_session(row)
    db.put_row(row)
    print("Prefetched session {row}")


def application(env, start_response):
    start_response('200 OK', [('Content-Type','text/html')])
    d = parse_qs(env["QUERY_STRING"])
    if "get_config" in d:
        guid = guidhelper.new_guid()
        return [json.dumps({
            "new_guid": guidhelper.new_guid(),
            "url": settings.get_url()
        }).encode()]
    if "guid" not in d:
        return error("Parameter guid required")
    guid = d["guid"][0]
    if guidhelper.validate_uuid4(guid):
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
            "redirect_uri": settings.get_url(),
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
        print("Creating thread...")
        t = threading.Thread(target=prefetch_session, args=(row,))
        print("Starting thread...")
        t.start()
        print("Thread running.")
    return [json.dumps({"success": "success"}).encode()]
