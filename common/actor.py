import requests
from Crypto.PublicKey import RSA
from Crypto.PublicKey.RSA import RsaKey

from .instance import Instance
from environ import Environ


class Actor:
    @staticmethod
    def url(
            actor_url: str,
            private_key_path: str = None,
    ):
        response = requests.get(actor_url, headers={"Accept": "application/activity+json"})
        if response.status_code // 100 != 2:
            raise FileNotFoundError(response)
        response = response.json()
        instance = Instance(response["id"])
        instance.path = "/"
        user = response["preferredUsername"]
        if private_key_path is not None:
            with open(private_key_path) as fp:
                private_key = RSA.import_key(fp.read())
            client_inbox = f"{instance}/users/{user}/inbox"
        else:
            private_key = None
            client_inbox = None
        return Actor(
            user,
            instance,
            client_inbox,
            private_key,
            **response
        )

    @staticmethod
    def webfinger(
            username: str,
            instance: str = None,
            private_key_path: str = None,
    ):
        username, instance = parse_username(username, instance)
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
        username, instance = parse_username(username, instance)
        id = f"{instance}/users/{username}"
        if private_key_path is not None:
            with open(private_key_path) as fp:
                private_key = RSA.import_key(fp.read())
        else:
            private_key = None
        if public_key_path is not None:
            with open(public_key_path) as fp:
                public_key_pem = fp.read()
        else:
            public_key_pem = None
        return Actor(
            username,
            instance,
            f"{instance}/users/{username}/inbox",
            private_key,
            id=id,
            inbox=f"{instance}/users/{username}/inbox",
            publicKey={"id": id, "publicKeyPem": public_key_pem}
        )

    def __init__(
            self,
            username: str,
            instance: Instance,
            client_inbox: str = None,
            private_key: RsaKey = None,
            /, *,
            id: str = None,
            inbox: str = None,
            publicKey: dict[str, str] = None,
            **kwargs
    ):
        publicKey = publicKey or {}
        self.username = username
        self.instance = instance
        self.full_username = f"@{username}@{instance.hostname}"
        self.client_inbox = client_inbox
        self.private_key = private_key
        self.id = id
        self.inbox = inbox
        self.public_key_id = publicKey.get("id")
        self.public_key_pem = publicKey.get("publicKeyPem")

    def __repr__(self):
        return f"<Actor {self.full_username}>"


def parse_username(
        username: str,
        instance: str = None,
        default_instance: str = Environ.INSTANCE,
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
