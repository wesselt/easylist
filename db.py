import psycopg2
import psycopg2.extras

import settings


def get_cursor():
    db = psycopg2.connect(settings.get_connection_string())
    db.autocommit = True
    return db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

 
def new_row(guid):
    return {
        "guid": guid,
        "code": None,
        "bearer": None,
        "private_key": None,
        "installation_token": None,
        "session_token": None,
    }


def get_row(guid):
    cur = get_cursor()
    cur.execute("select * from get_row(%s)", (guid, ))
    return cur.fetchone()


def put_row(row):
    cur = get_cursor()
    #print(f"saving row {row}")
    cur.execute("select put_row(%s, %s, %s, %s, %s, %s) as result", (
        row["guid"],
        row.get("code"),
        row.get("bearer"),
        row.get("private_key"),
        row.get("installation_token"),
        row.get("session_token"),
    ));
    result = cur.fetchone()["result"]
    if result not in (1,2):
        raise Exception(f"put_row() returned {result} for row {row}")
