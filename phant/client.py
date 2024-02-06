import datetime
import json
from typing import Any
from uuid import uuid4

import requests

from .actor import Actor
from .auth import signed_request, verify_request
from .datatypes import Mail


def register(
        username: str,
        instance: str = None,
        *,
        public_key_path: str,
        private_key_path: str
):
    actor = Actor.phant(username, instance, public_key_path=public_key_path)
    response = requests.post(actor.id, actor.public_key.export_key())
    if response.status_code // 100 != 2:
        raise RuntimeError("Unable to register actor.", actor, response)
    return Actor.url(actor.id, private_key_path=private_key_path)


def get_inbox(actor: Actor) -> list[dict[str, Any]]:
    response = signed_request(
        method="GET",
        endpoint=actor.inbox,
        sender=actor
    )
    if response.status_code // 100 != 2:
        raise RuntimeError("Unable to get inbox.", actor, response)
    valid_mails = []
    for mail in [Mail(**item) for item in response.json()]:
        error = verify_request(actor.instance, mail)
        if error is None:
            valid_mails.append(mail.content)
    return valid_mails


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
    if response.status_code // 100 != 2:
        raise RuntimeError("Unable to post activity.", response)


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
