from .endpoint import endpoint


@endpoint("/.well-known/webfinger")
def webfinger(resource: str = ""):
    return {}
