from urllib.parse import urlparse


class Instance:
    def __init__(
            self,
            url: str,
            default_scheme: str = "https"
    ):
        parsed = urlparse(url)
        if parsed.hostname is None:
            if parsed.scheme == "":
                parts = parsed.path.split("/")
                sub = parts[0].split(":")
                self.hostname = sub[0]
                self.port = sub[1] if len(sub) > 1 else None
                self.path = "/" + "/".join(parts[1:])
            else:
                self.hostname = parsed.scheme
                parts = parsed.path.split("/")
                self.port = int(parts[0])
                self.path = "/" + "/".join(parts[1:])
            if self.hostname == "127.0.0.1":
                self.scheme = "http"
            elif self.port == 80:
                self.scheme = "http"
            elif self.port == 443:
                self.scheme = "https"
            else:
                self.scheme = default_scheme
        else:
            self.scheme = parsed.scheme
            self.hostname = parsed.hostname
            self.port = parsed.port
            self.path = parsed.path or "/"

    def __str__(self):
        if self.port is None:
            return f"{self.scheme}://{self.hostname}"
        else:
            return f"{self.scheme}://{self.hostname}:{self.port}"

    def __eq__(self, other: 'Instance'):
        return all([
            self.scheme == other.scheme,
            self.hostname == other.hostname,
            self.port == other.port,
        ])

    def __repr__(self):
        return f"<URL {self}>"
