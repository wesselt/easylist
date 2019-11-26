import psycopg2
import psycopg2.extras

import secret


def get_cursor():
    db = psycopg2.connect("dbname='easylist' user='backend' " +
        f"host='127.0.0.1' password='{secret.get_db_password()}'")
    db.autocommit = True
    return db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

 
def get_row(guid):
    cur = get_cursor()
    cur.execute("select * from get_row(%s)", (guid, ))
    rows = cur.fetchall()
    if not rows:
      return None
    return rows[0]


def put_row(row):
    cur = get_cursor()
    print(f"saving row {row}")
    return cur.execute("select put_row(%s, %s, %s, %s, %s, %s)", (
        row["guid"],
        row.get("code"),
        row.get("bearer"),
        row.get("private_key"),
        row.get("installation_token"),
        row.get("session_token"),
    ))
