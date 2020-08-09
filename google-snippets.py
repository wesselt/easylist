import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient import discovery
from google.auth.transport.requests import Request
    
    #credobj = google.oauth2.credentials.Credentials(**creds)



    service = discovery.build('sheets', 'v4', credentials=credentials)
    spreadsheet = {
        'properties': {
            'title': "Easylist"
        }
    }
    spreadsheet = service.spreadsheets().create(body=spreadsheet,
                               fields='spreadsheetId,spreadsheetUrl').execute()
    spreadsheet_id = spreadsheet.get("spreadsheetId")
    body = {
        "values": [
            [1, "=A1+1"]
        ]
    }
    request = service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="A1",
        valueInputOption="USER_ENTERED",
        body=body)
    response = request.execute()
    return spreadsheet.get("spreadsheetUrl")






    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        settings.get_app_credentials(), 
        ['https://www.googleapis.com/auth/drive.file'])
    flow.redirect_uri = 'https://easylist.aule.net/dev/sheet'

    if "code" in d:
        url = "{}://{}{}".format(env["REQUEST_SCHEME"],
                                 env["SERVER_NAME"],
                                 env["REQUEST_URI"])
        flow.fetch_token(authorization_response=url)
        credentials = flow.credentials
        #result = {
        #    'token': credentials.token,
        #    'refresh_token': credentials.refresh_token,
        #    'token_uri': credentials.token_uri,
        #    'client_id': credentials.client_id,
        #    'client_secret': credentials.client_secret,
        #    'scopes': credentials.scopes
        #}
        sheet_url = create_sheet(credentials)
        start_response('302 Found', [('Location', sheet_url)])
        return

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        prompt='consent',
        include_granted_scopes='true')

    start_response('302 Found', [('Location', authorization_url)])
    return
