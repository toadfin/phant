import base64
import datetime
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

import Crypto.Hash
import Crypto.Signature.pkcs1_15
import requests
from Crypto.PublicKey import RSA

from .actor import Actor


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


def register(
        username: str,
        instance_url: str,
        public_key_path: str = None,
        public_key_pem: str = None,
):
    if not ((public_key_pem is None) ^ (public_key_path is None)):
        raise RuntimeError
    if public_key_path is not None:
        with open(public_key_path) as fp:
            public_key = fp.read()
    else:
        public_key = public_key_pem
    response = requests.post(f"{instance_url}/users/{username}", params={
        "public_key": public_key
    })
    if response.status_code // 100 != 2:
        raise RuntimeError(response.text)
    else:
        return response.json()


def post_activity(
        activity: dict[str, Any],
        sender: Actor,
        recipient: Actor,
        private_key_path: str,
        date: datetime.datetime = None
) -> dict[str, Any]:
    with open(private_key_path) as fp:
        private_key = RSA.import_key(fp.read())
    content = json.dumps(activity)
    hasher = Crypto.Hash.SHA256.new()
    hasher.update(content.encode("ascii"))
    digest = "sha-256=" + base64.b64encode(hasher.digest()).decode("ascii")
    inbox = urlparse(recipient.inbox)
    date = (date or datetime.datetime.now()).strftime("%a, %d %b %Y %H:%M:%S GMT")
    signed_string = f"(request-target): post {inbox.path}\n" \
                    f"digest: {digest}\n" \
                    f"host: {inbox.hostname}\n" \
                    f"date: {date}"
    signer = Crypto.Signature.pkcs1_15.new(private_key)
    hasher = Crypto.Hash.SHA256.new()
    hasher.update(signed_string.encode())
    signature = base64.b64encode(signer.sign(hasher)).decode("ascii")
    signature_header = f'keyId="{sender.public_key_id}",' \
                       f'headers="(request-target) digest host date",' \
                       f'signature="{signature}"'
    return requests.post(recipient.inbox, data=content, headers={
        'Digest': digest,
        'Host': inbox.hostname,
        'Date': date,
        'Signature': signature_header
    }).json()


def post_create_activity(
        object_activity: dict[str, Any],
        sender: Actor,
        recipient: Actor,
        private_key_path: str,
        date: datetime.datetime = None
) -> dict[str, Any]:
    return post_activity(
        activity={
            "@context": "https://www.w3.org/ns/activitystreams",
            "id": generate_id(sender),
            "type": "Create",
            "actor": sender.id,
            "object": object_activity
        },
        sender=sender,
        recipient=recipient,
        private_key_path=private_key_path,
        date=date,
    )


def post_note(
        content: str,
        sender: Actor,
        recipient: Actor,
        private_key_path: str,
        date: datetime.datetime = None
):
    date = date or datetime.datetime.now()
    return post_create_activity(
        object_activity={
            "id": generate_id(sender),
            "type": "Note",
            "published": date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "attributedTo": sender.id,
            "content": content,
            "to": recipient.id,
        },
        sender=sender,
        recipient=recipient,
        private_key_path=private_key_path,
        date=date
    )


def generate_id(actor: Actor):
    return f"{actor.id}/{uuid4()}"
