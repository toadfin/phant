from collections import defaultdict
from threading import Lock

from flask import request

from environ import Environ
from .utils import endpoint

if Environ.DEBUG:
    public_keys = defaultdict(lambda: {
        "id": "DEBUG_PUBLIC_KEY_ID",
        "owner": "DEBUG_PUBLIC_KEY_OWNER",
        "publicKeyPem": "DEBUG_PUBLIC_KEY_PEM"
    })
else:
    public_keys = {}
lock = Lock()


@endpoint("/.well-known/webfinger")
def webfinger(resource: str):
    parts = resource.split(":", maxsplit=1)
    if len(parts) != 2 or parts[0] != "acct":
        return "Invalid resource", 422
    parts = parts[1].split("@", maxsplit=1)
    if len(parts) != 2:
        return "Invalid resource", 422
    user = parts[0]
    lock.acquire()
    try:
        _ = public_keys[user]
    except NameError:
        return {}
    finally:
        lock.release()
    return {
        "subject": resource,
        "links": [
            {
                "rel": "self",
                "type": "application/activity+json",
                "href": f"{Environ.URL}/users/{user}"
            }
        ]
    }


@endpoint('/users/<user>')
def get_user(user: str):
    lock.acquire()
    try:
        public_key = public_keys[user]
    except NameError:
        return "User Not Found", 404
    finally:
        lock.release()
    public_key_pem = public_key.get("publicKeyPem", None)
    if public_key_pem is None:
        return "User Error", 500
    inbox = f"{Environ.URL}/users/{user}/inbox"
    accept_parts = request.headers.get("Accept", "").split(";")
    if len(accept_parts) > 0:
        return_json = "application/activity+json" in accept_parts[0].split(",")
    else:
        return_json = False
    if return_json:
        return {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                "https://w3id.org/security/v1"
            ],
            "id": f"{Environ.URL}/users/{user}",
            "type": "Person",
            "preferredUsername": user,
            "inbox": inbox,
            "publicKey": {
                "id": f"{Environ.URL}/users/{user}/public_key",
                "owner": f"{Environ.URL}/users/{user}",
                "publicKeyPem": public_key_pem
            }
        }
    else:
        return f"""<h1>{user}</h1>
        <b>Inbox:</b> {inbox}<br>
        <b>Public Key:</b><br>{public_key_pem}"""


@endpoint('/users/<user>', methods=("POST",))
def register_user(user: str, public_key: str):
    new_public_key = {
        "id": f"{Environ.URL}/users/{user}/public_key",
        "owner": f"{Environ.URL}/users/{user}",
        "publicKeyPem": public_key
    }
    lock.acquire()
    try:
        old_public_key = public_keys[user]
    except NameError:
        public_keys[user] = new_public_key
        return True
    else:
        old_public_key_pem = old_public_key.get("publicKeyPem", None)
        if old_public_key_pem is None:
            public_keys[user] = new_public_key
            return True
        elif old_public_key_pem != public_key:
            return "User Already Exists", 409
        else:
            return True
    finally:
        lock.release()


@endpoint('/users/<user>/public_key')
def get_user_public_key(user: str):
    lock.acquire()
    try:
        public_key = public_keys[user]
    except NameError:
        return "Public key not found", 404
    else:
        return public_key
    finally:
        lock.release()
