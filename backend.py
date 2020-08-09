import json
import requests
import sys
import threading
from urllib.parse import parse_qs

import bunq
import db
import guidhelper
import settings


def error(message):
    return [json.dumps({"error": message}).encode()]


def prefetch_session(row):
    print(f"Prefetching {row['guid']}...")
    bunq.get_session_token(row)
    print(f"Done prefetching {row['guid']}")


def application(env, start_response):
    start_response('200 OK', [('Content-Type','text/html')])
    d = parse_qs(env["QUERY_STRING"])
    if "get_config" in d:
        guid = guidhelper.new_guid()
        return [json.dumps({
            "new_guid": guidhelper.new_guid(),
            "client_id": settings.get_client_id(),
            "oauth_url": settings.get_oauth_url(),
            "url": settings.get_url(),
            "dev_url": settings.get_dev_url(),
            "sandbox_url": settings.get_sandbox_url(),
            "prod_url": settings.get_prod_url(),
        }).encode()]
    if "guid" not in d:
        return error("Parameter guid required")
    guid = d["guid"][0]
    if guidhelper.validate_uuid4(guid):
        return error("Parameter guid must be a valid guid")
    code = d["code"][0] if "code" in d else ""
    row = db.get_row(guid)
    if not row:
        row = db.new_row(guid)
    if code and not row["code"]:
        row["code"] = code
        db.put_row(row)
    if not row.get("bearer"):
        if not code:
            return error("Parameter code required for guid without bearer")
        url = settings.get_token_url() + "v1/token"
        response = requests.post(url, params={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.get_url(),
            "client_id": settings.get_client_id(),
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
