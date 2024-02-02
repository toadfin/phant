from typing import Type

from .activities import Activity
from .exceptions import ActorNotFound
from .http import get, post


class Actor:
    def __init_subclass__(cls, **kwargs):
        actor_types[cls.__name__] = cls

    @classmethod
    async def webfinger(cls, username: str, host: str, ssl: bool = True):
        scheme = "https" if ssl else "http"
        response = await get(
            f"{scheme}://{host}/.well-known/webfinger",
            params={"resource": f"acct:{username}@{host}"}
        )
        for link in response.get("links", ()):
            if link.get("rel", None) == "self":
                actor_url = link.get("href", None)
                break
        else:
            actor_url = None
        if actor_url is None:
            raise ActorNotFound
        response = await get(actor_url, headers={"Accept": "application/activity+json"})
        actor_type = actor_types[response.get("type", Actor.__name__)]
        return actor_type(**response)

    def __init__(self, **kwargs):
        self._id = kwargs.get("id", None)
        self._inbox = kwargs.get("inbox", None)
        self._public_key = kwargs.get("publicKey", {}).get("publicKeyPem", None)

    async def post_activity(self, activity: Activity):
        activity.object = self._id
        response = await post(self._inbox, json=activity.to_dict())
        pass


actor_types: dict[str, Type[Actor]] = {Actor.__name__: Actor}


class Person(Actor):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
