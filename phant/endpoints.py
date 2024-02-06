import json
from collections import defaultdict
from urllib.parse import urlparse

from Crypto.PublicKey import RSA
from flask import request

from .actor import Actor
from .datatypes import Mail
from .server import endpoint, phant_instance, server_verifier

global_inbox: dict[str, list[Mail]] = defaultdict(list)


@endpoint("/.well-known/webfinger")
def webfinger(resource: str):
    parts = resource.split(":", maxsplit=1)
    if len(parts) != 2 or parts[0] != "acct":
        return "Invalid resource", 422
    parts = parts[1].split("@", maxsplit=1)
    if len(parts) != 2:
        return "Invalid resource", 422
    user = parts[0]
    id = get_phant_id(user)
    try:
        _ = server_verifier.get_key(id)
    except KeyError:
        return {}
    else:
        return {
            "subject": resource,
            "links": [
                {
                    "rel": "self",
                    "type": "application/activity+json",
                    "href": f"{phant_instance[0]}/users/{user}"
                }
            ]
        }


@endpoint('/users/<user>')
def get_user(user: str):
    id = get_phant_id(user)
    try:
        public_key = server_verifier.get_key(id)
    except KeyError:
        return "User Not Found", 404
    accept_parts = request.headers.get("Accept", "").split(";")
    if len(accept_parts) > 0:
        return_json = "application/activity+json" in accept_parts[0].split(",")
    else:
        return_json = False
    inbox = f"{id}/inbox"
    if return_json:
        return {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                "https://w3id.org/security/v1"
            ],
            "id": id,
            "type": "Person",
            "preferredUsername": user,
            "inbox": inbox,
            "publicKey": {
                "id": id,
                "owner": id,
                "publicKeyPem": public_key.public_key().export_key().decode()
            }
        }
    else:
        return f"""<h1>{user}</h1>
        <b>Inbox:</b> {inbox}<br>
        <b>Public Key:</b><br>{public_key}"""


@endpoint('/users/<user>', methods=("POST",))
def register_user(user: str):
    id = get_phant_id(user)
    public_key = RSA.import_key(request.data.decode())
    try:
        old_public_key_pem = server_verifier.get_key(id)
    except KeyError:
        server_verifier.set_key(id, public_key)
    else:
        if old_public_key_pem is None:
            server_verifier.set_key(id, public_key)
        elif old_public_key_pem != public_key:
            return "User Already Exists", 409


@endpoint('/external_keys', methods=("POST",))
def register_external_user():
    actor = Actor.json(request.json)
    server_verifier.set_key(actor.public_key_id, actor.public_key)


@endpoint("/users/<user>/inbox", signed=True)
def inbox_get(user: str):
    inbox = tuple(global_inbox[user])
    global_inbox[user].clear()
    return list(inbox)


@endpoint("/users/<user>/inbox", methods=("POST",), signed=True)
def inbox_post(user: str):
    if request.is_json:
        activity = request.json
    else:
        activity = json.loads(request.data.decode())
    recipients = activity.get("to")
    if recipients is None:
        return "Missing field: to", 409
    elif isinstance(recipients, str):
        recipients = (recipients,)
    elif not isinstance(recipients, list):
        return "Invalid type for field: to", 409
    mail = Mail(
        method=request.method,
        path=request.path,
        data=request.data,
        headers=dict(request.headers),
        content_type=request.content_type,
    ).to_dict()
    for recipient in recipients:
        recipient_user = urlparse(recipient).path.split("/")[2]
        if recipient_user != user:
            return f"Invalid recipient in field to: {recipient_user}", 409
        global_inbox[user].append(mail)


@endpoint("robots.txt")
def robots():
    return """# See http://www.robotstxt.org/robotstxt.html for documentation on how to use the robots.txt file

User-agent: GPTBot
Disallow: /

User-agent: *
Disallow: /media_proxy/
Disallow: /interact/
"""


@endpoint(".well-known/nodeinfo")
def node_info():
    return {
        "links": [
            {
                "rel": "http://nodeinfo.diaspora.software/ns/schema/2.0",
                "href": f"{phant_instance[0]}/nodeinfo/2.0"
            }
        ]
    }


@endpoint("nodeinfo/2.0")
def node_info():
    return {
        "version": "2.0",
        "software": {
            "name": "phant",
            "version": "0.0.1"
        },
        "protocols": [
            "activitypub"
        ],
        "services": {
            "outbound": [],
            "inbound": []
        },
        "openRegistrations": True,
        "metadata": {
            "nodeName": "Phant",
            "nodeDescription": "The sound that phants make"
        }
    }


@endpoint("/api/v1/instance")
def mastodon_instance():
    return {
        "uri": phant_instance[0].hostname,
        "title": "Phant",
        "short_description": "The sound that phants make",
        "description": "",
        "version": "0.0.1",
        "languages": [
            "en", "it"
        ],
        "registrations": False,
        "approval_required": False,
        "invites_enabled": False,
        "rules": [
            {
                "id": "1",
                "text": "Phants never forget"
            },
            {
                "id": "2",
                "text": "Phants will always search for you"
            },
            {
                "id": "3",
                "text": "Phants won't stop"
            },
            {
                "id": "4",
                "text": "Phant is already behind you"
            },
            {
                "id": "7",
                "text": "You better not turn around"
            }
        ]
    }


def get_phant_id(user: str):
    return f"{phant_instance[0]}/users/{user}"
