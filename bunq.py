import base64
from OpenSSL import crypto
import json
import os
import requests
import socket
import sys

import db
import settings


# 1 to log http calls, 2 to include headers
log_level = 0

# Pagination
older_url = None


# -----------------------------------------------------------------------------

def get_private_key(row):
    pem_str = row["private_key"]
    if pem_str:
        return crypto.load_privatekey(crypto.FILETYPE_PEM, pem_str)
    print("Generating new private key...")
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 2048)
    pem = crypto.dump_privatekey(crypto.FILETYPE_PEM, key)
    row["private_key"] = pem.decode("utf-8")
    db.put_row(row)
    return key


def get_public_key(row):
    private_key = get_private_key(row)
    pem = crypto.dump_publickey(crypto.FILETYPE_PEM, private_key)
    return crypto.load_publickey(crypto.FILETYPE_PEM, pem)


def get_installation_token(row):
    token = row["installation_token"]
    if token:
        return token
    print("Requesting installation token...")
    public_key = get_public_key(row)
    pem = crypto.dump_publickey(crypto.FILETYPE_PEM, public_key)
    method = "v1/installation"
    data = {
        "client_public_key": pem.decode("utf-8")
    }
    reply = post(row, method, data)
    installation_token = server_public = None
    for line in reply:
        if "Token" in line:
            installation_token = line["Token"]["token"]
    if not installation_token:
        raise Exception("No token returned by installation")
    row["installation_token"] = installation_token
    register_device(row)
    db.put_row(row)
    return installation_token


def register_device(row):
    ip = "172.105.76.249"
    print("Registering IP " + ip)
    method = "v1/device-server"
    data = {
        "description": "easylist on easylist.aule.net",
        "secret": row["bearer"],
        "permitted_ips": [ip]
    }
    post(row, method, data)


def get_session_token(row):
    token = row["session_token"]
    if token:
        return token.rstrip("\r\n")
    print("Requesting session token...")
    method = "v1/session-server"
    data = {
        "secret": row["bearer"],
    }
    reply = post(row, method, data)
    session_token = None
    for line in reply:
        if "Token" in line:
            session_token = line["Token"]["token"]
    if not session_token:
        raise Exception("No token returned by session-server")
    row["session_token"] = session_token
    db.put_row(row)
    return session_token


# -----------------------------------------------------------------------------

def sign(row, action, method, headers, data):
    # Installation requests are not signed
    if method.startswith("v1/installation"):
        return
    # device-server and session-server use the installation token
    # Other endpoints use a session token
    if not (method.startswith("v1/device-server") or
            method.startswith("v1/session-server")):
        headers['X-Bunq-Client-Authentication'] = get_session_token(row)
        if not (action == "POST" and method.endswith("/payment")):
            return
    else:
        headers['X-Bunq-Client-Authentication'] = get_installation_token(row)

    # Device-server and session-server must be signed
    private_key = get_private_key(row)
    sig = crypto.sign(private_key, data, 'sha256')
    sig_str = base64.b64encode(sig).decode("utf-8")
    headers['X-Bunq-Client-Signature'] = sig_str


# -----------------------------------------------------------------------------

def log_request(action, method, headers, data):
    if log_level < 1:
        return
    print("******************************")
    print("{0} {1}".format(action, method))
    if log_level > 1:
        for k, v in headers.items():
            print("  {0}: {1}".format(k, v))
    if data:
        print("-----")
        print(json.dumps(data, indent=2))
        print("-----")


def log_reply(reply):
    if log_level < 1:
        return
    print("Status: {0}".format(reply.status_code))
    if log_level > 1:
        for k, v in reply.headers.items():
            print("  {0}: {1}".format(k, v))
    print("----------")
    if reply.headers["Content-Type"] == "application/json":
        print(json.dumps(reply.json(), indent=2))
    else:
        print(reply.text)
    print("******************************")


def call_requests(row, action, method, data_obj):
    data = json.dumps(data_obj) if data_obj else ''
    headers = {
        'Cache-Control': 'no-cache',
        'User-Agent': 'easylist',
    }
    sign(row, action, method, headers, data)
    log_request(action, method, headers, data_obj)
    url = settings.get_bunq_url()
    if action == "GET":
        reply = requests.get(url + method, headers=headers)
    elif action == "POST":
        reply = requests.post(url + method, headers=headers, data=data)
    log_reply(reply)
    if reply.headers["Content-Type"] == "application/json":
        return reply.json()
    return reply.text


def call(row, action, method, data=None):
    result = call_requests(row, action, method, data)
    if isinstance(result, str):
        return result
    if ("Error" in result and result["Error"][0]["error_description"] in (
            "Insufficient authorisation.",
            "Insufficient authentication.")):
        row["session_token"] = ""
        print("Clearing session token...")
        result = call_requests(row, action, method, data)
        if isinstance(result, str):
            return result
    if "Error" in result:
        raise Exception(result["Error"][0]["error_description"])
    global older_url
    older_url = result.get("Pagination", {}).get("older_url")
    return result["Response"]


# -----------------------------------------------------------------------------

def set_log_level(level):
    global log_level
    log_level = level


def get(row, method):
    return call(row, 'GET', method)


def has_previous():
    return older_url is not None


def previous(row):
    if not older_url:
        return []
    return call(row, 'GET', older_url.lstrip("/"))


def post(row, method, data):
    return call(row, 'POST', method, data)
