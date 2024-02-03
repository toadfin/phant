from urllib.parse import urlparse

import requests

from .exceptions import ActorNotFound


class Actor:
    @classmethod
    def webfinger(
            cls,
            username: str,
            instance_url: str
    ):
        response = requests.get(
            f"{instance_url}/.well-known/webfinger",
            params={"resource": f"acct:{username}@{urlparse(instance_url).hostname}"}
        )
        for link in response.json().get("links", ()):
            if link.get("rel", None) == "self":
                actor_url = link.get("href", None)
                break
        else:
            actor_url = None
        if actor_url is None:
            raise ActorNotFound(username)
        response = requests.get(actor_url, headers={"Accept": "application/activity+json"})
        if response.status_code // 100 != 2:
            raise ActorNotFound(response)
        return Actor(**response.json())

    @classmethod
    def stub(
            cls,
            username: str = None,
            instance_url: str = None,
    ):
        return Actor(
            id=f"{instance_url}/users/{username}",
            inbox=f"{instance_url}/users/{username}/inbox",
            publicKey={"id": f"{instance_url}/users/{username}/public_key"}
        )

    def __init__(
            self,
            id: str = None,
            inbox: str = None,
            publicKey: dict[str, str] = None,
            **kwargs
    ):
        self.id = id
        self.inbox = inbox
        self.public_key_id = (publicKey or {}).get("id", None)

    def get_private_key(self):
        return requests.get(self.public_key_id).json()
