import base64
import datetime
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import Crypto.Hash.SHA256
import Crypto.Signature.pkcs1_15
import requests
from Crypto.PublicKey import RSA

from common import Actor, Instance


def make_keys(
        private_key_path: str,
        public_key_path: str
):
    private_key_path = Path(private_key_path)
    public_key_path = Path(public_key_path)
    if private_key_path.exists() or public_key_path.exists():
        raise FileExistsError
    key_pair = RSA.generate(3072)
    private_key = key_pair.export_key().decode("ascii")
    with open(private_key_path, "w") as fp:
        fp.write(private_key)
    public_key = key_pair.public_key().export_key().decode("ascii")
    with open(public_key_path, "w") as fp:
        fp.write(public_key)


def signed_request(
        method: str,
        endpoint: str,
        sender: Actor,
        content: str = "",
        date: datetime.datetime = None,
        **kwargs
):
    if sender.private_key is None:
        raise ValueError(f"No available private key for actor {sender.full_username}")
    url = Instance(endpoint)
    date = date or datetime.datetime.utcnow()
    if "headers" in kwargs:
        headers = kwargs["headers"]
        del kwargs["headers"]
    else:
        headers = {}
    hasher = Crypto.Hash.SHA256.new()
    hasher.update(content.encode("ascii"))
    digest = "sha-256=" + base64.b64encode(hasher.digest()).decode("ascii")
    date_str = date.strftime("%a, %d %b %Y %H:%M:%S GMT")
    signed_string = f"(request-target): {method.lower()} {url.path}\n" \
                    f"digest: {digest}\n" \
                    f"host: {url.hostname}\n" \
                    f"date: {date_str}"
    signer = Crypto.Signature.pkcs1_15.new(sender.private_key)
    hasher = Crypto.Hash.SHA256.new()
    hasher.update(signed_string.encode())
    signature = base64.b64encode(signer.sign(hasher)).decode("ascii")
    signature_header = f'keyId="{sender.public_key_id}",' \
                       f'headers="(request-target) digest host date",' \
                       f'signature="{signature}"'
    return requests.request(method, endpoint, data=content, headers=dict(
        headers,
        Digest=digest,
        Host=url.hostname,
        Date=date_str,
        Signature=signature_header
    ), **kwargs)


def register(actor: Actor):
    response = requests.post(
        f"{actor.instance}/users/{actor.username}",
        actor.public_key_pem,
    )
    if response.status_code // 100 != 2:
        raise RuntimeError(response.text, response.status_code)


def get_inbox(actor: Actor) -> list[dict[str, Any]]:
    response = signed_request(
        method="GET",
        endpoint=actor.client_inbox,
        content="",
        sender=actor
    )
    if response.status_code != 200:
        raise RuntimeError(response.text, response.status_code)
    else:
        return response.json()


def wait_inbox(actor: Actor):
    inbox = ()
    while len(inbox) == 0:
        inbox = get_inbox(actor)
    return inbox


def post_activity(
        activity: dict[str, Any],
        sender: Actor,
        recipient: Actor,
        date: datetime.datetime = None,
):
    response = signed_request(
        method="POST",
        endpoint=recipient.inbox,
        content=json.dumps(activity),
        sender=sender,
        date=date,
    )
    return response.status_code // 100 == 2


def post_activity_create(
        object_activity: dict[str, Any],
        sender: Actor,
        recipient: Actor,
        date: datetime.datetime = None
):
    date = date or datetime.datetime.now()
    return post_activity(
        activity={
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                {
                    "ostatus": "http://ostatus.org#",
                    "atomUri": "ostatus:atomUri",
                    "inReplyToAtomUri": "ostatus:inReplyToAtomUri",
                    "conversation": "ostatus:conversation",
                    "sensitive": "as:sensitive",
                    "toot": "http://joinmastodon.org/ns#",
                    "votersCount": "toot:votersCount"
                }
            ],
            "id": generate_id(sender),
            "type": "Create",
            "actor": sender.id,
            "published": date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "to": [recipient.id],
            "cc": [],
            "object": object_activity
        },
        sender=sender,
        recipient=recipient,
        date=date,
    )


def post_note(
        content: str,
        sender: Actor,
        recipient: Actor,
        date: datetime.datetime = None,
        summary: str = None,
        in_reply_to: str = None,
        in_reply_to_atom_uri: str = None,
        sensitive: bool = False,
):
    id_convo = uuid4().fields[0]
    id_note = generate_id(sender, id_convo)
    date = date or datetime.datetime.now()
    return post_activity_create(
        object_activity={
            "id": id_note,
            "type": "Note",
            "summary": summary,
            "inReplyTo": in_reply_to,
            "published": date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "url": id_note,
            "attributedTo": sender.id,
            "to": [recipient.id],
            "cc": [],
            "sensitive": sensitive,
            "atomUri": id_note,
            "inReplyToAtomUri": in_reply_to_atom_uri,
            "conversation": f"tag:{sender.instance},{date.strftime('%Y-%m-%d')}:"
                            f"objectId={id_convo}:"
                            f"objectType=Conversation",
            "content": content,
            "contentMap": {},
            "attachment": [],
            "tag": [
                {
                    "type": "Mention",
                    "href": recipient.id,
                    "name": recipient.full_username
                }
            ],
            "replies": {
                "id": id_note,
                "type": "Collection",
                "first": {
                    "type": "CollectionPage",
                    "next": id_note,
                    "partOf": id_note,
                    "items": []
                }
            }
        },
        sender=sender,
        recipient=recipient,
        date=date,
    )


def generate_id(actor: Actor, id: int = None):
    id = id or uuid4().fields[0]
    return f"{actor.id}/{id}"
