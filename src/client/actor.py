from typing import overload
from urllib.parse import urlparse

import requests


class Actor:
    @classmethod
    @overload
    def webfinger(cls, full_username: str):
        ...

    @classmethod
    @overload
    def webfinger(cls, username: str, instance: str):
        ...


    @classmethod
    def webfinger(
            cls,
            username: str,
            instance: str = None
    ):
        if instance is None:
            parts = username.split("@")
            if len(parts) == 2:
                username = parts[0]
                instance = parts[1]
            elif len(parts) == 3:
                username = parts[1]
                instance = parts[2]
            else:
                raise ValueError(username)
        instance_url = urlparse(instance)
        scheme = instance_url.scheme or "https"
        hostname = instance_url.hostname or instance
        response = requests.get(
            f"{scheme}://{hostname}/.well-known/webfinger",
            params={"resource": f"acct:{username}@{hostname}"}
        )
        for link in response.json().get("links", ()):
            if link.get("rel") == "self":
                actor_url = link.get("href")
                break
        else:
            actor_url = None
        if actor_url is None:
            raise FileNotFoundError(username)
        response = requests.get(actor_url, headers={"Accept": "application/activity+json"})
        if response.status_code // 100 != 2:
            raise FileNotFoundError(response)
        return Actor(username, hostname, **response.json())

    @classmethod
    def stub(
            cls,
            username: str,
            instance_url: str,
            public_key_path: str,
    ):
        with open(public_key_path) as fp:
            public_key_pem = fp.read()
        return Actor(
            username,
            urlparse(instance_url).hostname,
            id=f"{instance_url}/users/{username}",
            inbox=f"{instance_url}/users/{username}/inbox",
            publicKey={"publicKeyPem": public_key_pem}
        )

    def __init__(
            self,
            username: str,
            instance: str,
            id: str = None,
            inbox: str = None,
            publicKey: dict[str, str] = None,
            **kwargs
    ):
        publicKey = publicKey or {}
        self.username = username
        self.instance = instance
        self.full_username = f"@{username}@{instance}"
        self.id = id
        self.inbox = inbox
        self.public_key_id = publicKey.get("id")
        self.public_key_pem = publicKey.get("publicKeyPem")

    def get_public_key(self):
        return self.public_key_pem

    def __repr__(self):
        return f"<Actor {self.username}@{self.instance}>"
