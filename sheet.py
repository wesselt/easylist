import urllib.parse
import json
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


class Sheet:

    def __init__(self, env, start_response):
        self.env = env
        self.start_response = start_response
        self.row = None


    def get_url(self):
        return "{}://{}{}".format(self.env["REQUEST_SCHEME"],
                                  self.env["SERVER_NAME"],
                                  self.env["REQUEST_URI"])

    def error(self, message):
        if self.row and self.row.get("bearer"):
            retry = (settings.get_url() + "sheet?state=" + self.guid +
                "&createsheet=1")
        else:
            retry = settings.get_url() + "sheet"

        if not isinstance(message, str):
            message = json.dumps(message)
        error_url = "error.html?error={}&retry={}".format(
            urllib.parse.quote(message),
            urllib.parse.quote(retry))
        self.start_response('302 Found', [('Location', error_url)])
        return []


    def get_flow(self):
        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            settings.get_app_credentials(), 
            ['https://www.googleapis.com/auth/drive.file'])
        flow.redirect_uri = settings.get_url() + "sheet"
        return flow


    # -----------------------------------------------------------------------------

    def request_bunq_oauth(self):
        url = (settings.get_oauth_url() + 'auth?' +
               'response_type=code&' +
               'client_id=' + settings.get_client_id() + '&' +
               'redirect_uri=' + settings.get_url() + 'sheet&' +
               'state=' + guidhelper.new_guid())
        self.start_response('302 Found', [('Location', url)])
        return []


    def create_bunq_installation(self, code):
        url = settings.get_token_url() + "v1/token"
        response = requests.post(url, params={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.get_url() + "sheet",
            "client_id": settings.get_client_id(),
            "client_secret": settings.get_client_secret()
        }).json()
        if "error" in response:
            return self.error(response)
        if "access_token" not in response:
            return self.error({
                "error": "No access_token returned", 
                "raw_reply": response
            })
        self.row = db.new_row(self.guid)
        self.row["bearer"] = response["access_token"]
        db.put_row(self.row)
        return self.request_google_oauth()


    def request_google_oauth(self):
        flow = self.get_flow()
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            prompt='consent',
            state=self.guid,
            include_granted_scopes='true')
        self.start_response('302 Found', [('Location', authorization_url)])
        return []


    def create_sheet(self, code):
        url = self.get_url()
        flow = self.get_flow()
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

        csv_url = settings.get_url() + "generate?guid=" + self.guid
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

        body = {
          "requests": [
             {
               "repeatCell": {
                 "range": {
                   "sheetId": 0,
                   "startColumnIndex": 2,
                   "endColumnIndex": 3
                 },
                 "cell": {
                   "userEnteredFormat": {
                     "numberFormat": {
                       "type": "DATE"
                     }
                   }
                 },
                 "fields": "userEnteredFormat.numberFormat"
              }
            }
          ]
        }
        request = service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body)
        response = request.execute()

        sheet_url = spreadsheet.get("spreadsheetUrl")
        self.start_response('302 Found', [('Location', sheet_url)])
        return []

    def run(self):
        d = urllib.parse.parse_qs(self.env["QUERY_STRING"])
        if not "state" in d:
            return self.request_bunq_oauth()
        self.guid = d["state"][0]
        if not guidhelper.validate_uuid4(self.guid):
            return self.error("State must be a valid guid")
        self.row = db.get_row(self.guid)
        if "error" in d:
            return self.error(d["error"][0])
        if "createsheet" in d:
            if not self.row or not self.row.get("bearer"):
                return self.error("BUNQ token required to create sheet")
            return self.request_google_oauth()
        if "code" not in d:
            return error("Parameter code expected")
        code = d["code"][0]
        if not self.row:
            return self.create_bunq_installation(code)
        return self.create_sheet(code)


def application(env, start_response):
    sheet = Sheet(env, start_response)
    return sheet.run()
