def get_client_id():
    return "your client id here"

def get_client_secret():
    return "your client secret here"

def get_connection_string():
   # Example connection string:
   # "host='127.0.0.1' dbname='easylist' user='goofy' password='topsecret'"
   return "your postgres connection string here"

def get_url():
    return get_prod_url()

def get_dev_url():
   return "https://easylist.aule.net/dev/"

def get_sandbox_url():
   return "https://easylist.aule.net/sandbox/"

def get_prod_url():
   return "https://easylist.aule.net/"

def get_bunq_url():
    return "https://api.bunq.com/"
    #return "https://public-api.sandbox.bunq.com/"

def get_oauth_url():
    return "https://oauth.bunq.com/"
    #return "https://oauth.sandbox.bunq.com/"

def get_token_url():
    return "https://api.oauth.bunq.com/"
    #return "https://api-oauth.sandbox.bunq.com/"
