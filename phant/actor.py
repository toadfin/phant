from typing import Any

import requests

from .keys import load_key, load_key_pem, import_key
from .instance import Instance


class Actor:
    @staticmethod
    def json(data: dict[str, Any], private_key_path: str = None):
        return Actor(
            data["preferredUsername"],
            Instance(data["id"]),
            private_key_path,
            **data
        )

    @staticmethod
    def url(
            actor_url: str,
            private_key_path: str = None,
    ):
        response = requests.get(actor_url, headers={"Accept": "application/activity+json"})
        if response.status_code // 100 != 2:
            raise FileNotFoundError(response)
        return Actor.json(response.json(), private_key_path)

    @staticmethod
    def webfinger(
            username: str,
            instance: str = None,
            private_key_path: str = None,
    ):
        username, instance = _parse_username(username, instance)
        response = requests.get(
            f"{instance}/.well-known/webfinger",
            params={"resource": f"acct:{username}@{instance.hostname}"}
        )
        for link in response.json().get("links", ()):
            if link.get("rel") == "self":
                actor_url = link.get("href")
                break
        else:
            actor_url = None
        if actor_url is None:
            raise FileNotFoundError(username)
        return Actor.url(actor_url, private_key_path)

    @staticmethod
    def phant(
            username: str,
            instance: str = None,
            private_key_path: str = None,
            public_key_path: str = None,
    ):
        username, instance = _parse_username(username, instance)
        actor_url = f"{instance}/users/{username}"
        return Actor(
            username,
            instance,
            private_key_path,
            id=actor_url,
            inbox=f"{actor_url}/inbox",
            publicKey={"id": actor_url, "publicKeyPem": load_key_pem(public_key_path)}
        )

    def __init__(
            self,
            username: str,
            instance: Instance,
            private_key_path: str = None,
            /,
            **kwargs
    ):
        self.json = kwargs
        public_key = kwargs.get("publicKey", {})
        self.username = username
        self.instance = instance
        self.full_username = f"@{username}@{instance.hostname}"
        self.private_key = load_key(private_key_path)
        self.id = kwargs.get("id")
        self.inbox = kwargs.get("inbox")
        self.public_key_id = public_key.get("id")
        self.public_key = import_key(public_key.get("publicKeyPem"))

    def __repr__(self):
        return f"<Actor {self.full_username}>"


def _parse_username(
        username: str,
        instance: str = None,
        default_instance: str = None,
        default_scheme: str = "https",
):
    parts = username.split("@")
    if len(parts) == 1:
        parsed_user = parts[0]
        parsed_instance = instance or default_instance
    elif len(parts) == 2:
        parsed_user = parts[0]
        parsed_instance = parts[1]
    elif len(parts) == 3:
        parsed_user = parts[1]
        parsed_instance = parts[2]
    else:
        raise ValueError(username)
    parsed_url = Instance(parsed_instance, default_scheme)
    if instance is not None:
        url = Instance(instance)
        if parsed_url != url:
            raise ValueError
    return parsed_user, parsed_url
