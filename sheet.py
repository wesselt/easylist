from urllib.parse import parse_qs
import json
import os
from pprint import pprint
import requests

import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient import discovery
from google.auth.transport.requests import Request
    
import bunq
import db
import guidhelper
import settings


def error(message):
    return [json.dumps({"error": message}).encode()]


def get_flow():
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        settings.get_app_credentials(), 
        ['https://www.googleapis.com/auth/drive.file'])
    flow.redirect_uri = 'https://easylist.aule.net/dev/sheet'
    return flow


# -----------------------------------------------------------------------------

def request_bunq_oauth(env, start_response):
    url = (settings.get_oauth_url() + 'auth?' +
           'response_type=code&' +
           'client_id=' + settings.get_client_id() + '&' +
           'redirect_uri=' + settings.get_url() + 'sheet&' +
           'state=' + guidhelper.new_guid())
    start_response('302 Found', [('Location', url)])
    return []


def create_bunq_installation(env, start_response, guid, code):
    row = db.new_row(guid)
    url = settings.get_token_url() + "v1/token"
    response = requests.post(url, params={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.get_sheet_url(),
        "client_id": settings.get_client_id(),
        "client_secret": settings.get_client_secret()
    }).json()
    if "error" in response:
        start_response('200 OK', [('Content-Type','text/json')])
        return [json.dumps(response).encode()]
    if "access_token" not in response:
        start_response('200 OK', [('Content-Type','text/json')])
        return [json.dumps({"error": "No access_token returned", 
                            "raw_reply": response}).encode()]
    row["bearer"] = response["access_token"]
    db.put_row(row)
    flow = get_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        prompt='consent',
        state=guid,
        include_granted_scopes='true')
    start_response('302 Found', [('Location', authorization_url)])
    return []


def create_sheet(env, start_response, guid, code):
    url = "{}://{}{}".format(env["REQUEST_SCHEME"],
                             env["SERVER_NAME"],
                             env["REQUEST_URI"])
    flow = get_flow()
    flow.fetch_token(authorization_response=url)
    credentials = flow.credentials
    service = discovery.build('sheets', 'v4', credentials=credentials)
    spreadsheet = {
        'properties': {
            'title': "Easylist"
        }
    }
    spreadsheet = service.spreadsheets().create(body=spreadsheet,
                               fields='spreadsheetId,spreadsheetUrl').execute()
    spreadsheet_id = spreadsheet.get("spreadsheetId")
    csv_url = settings.get_url() + "generate?guid=" + guid
    body = {
        "values": [
            ['=importdata("' + csv_url + '")']
        ]
    }
    request = service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="A1",
        valueInputOption="USER_ENTERED",
        body=body)
    response = request.execute()
    sheet_url = spreadsheet.get("spreadsheetUrl")
    start_response('302 Found', [('Location', sheet_url)])
    return []


def application(env, start_response):
    d = parse_qs(env["QUERY_STRING"])
    if "error" in d:
        start_response('200 OK', [('Content-Type','text/json')])
        return error(d["error"][0])
    if not "state" in d:
        return request_bunq_oauth(env, start_response)
    state = d["state"][0]
    if guidhelper.validate_uuid4(state):
        return error("State must be a valid guid")
    if "code" not in d:
        start_response('200 OK', [('Content-Type','text/json')])
        return error("Parameter code expected")
    code = d["code"][0]
    row = db.get_row(state)
    if not row:
        return create_bunq_installation(env, start_response, state, code)
    return create_sheet(env, start_response, state, code)
