class Activity:
    context = "https://www.w3.org/ns/activitystreams"
    object: str

    def __init__(self, id: str, type: str, actor: str):
        self.id = id
        self.type = type
        self.actor = actor

    def to_dict(self):
        return {
            "@context": self.context,
            "id": self.id,
            "type": self.type,
            "actor": self.actor,
            "object": self.object,
        }


class Follow(Activity):
    def __init__(self, id: str, actor: str):
        Activity.__init__(self, id, "Follow", actor)
