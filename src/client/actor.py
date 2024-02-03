from urllib.parse import urlparse

import requests


class Actor:
    @classmethod
    def webfinger(
            cls,
            username: str,
            instance_url: str
    ):
        hostname = urlparse(instance_url).hostname
        response = requests.get(
            f"{instance_url}/.well-known/webfinger",
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
        self.id = id
        self.inbox = inbox
        self.public_key_id = publicKey.get("id")
        self.public_key_pem = publicKey.get("publicKeyPem")

    def get_public_key(self):
        return self.public_key_pem

    def __repr__(self):
        return f"<Actor {self.username}@{self.instance}>"
