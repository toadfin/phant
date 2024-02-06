from pathlib import Path

from Crypto.PublicKey import RSA


def generate_keys(
        private_key_path: str,
        public_key_path: str
):
    private_key_path = Path(private_key_path)
    public_key_path = Path(public_key_path)
    if private_key_path.exists() or public_key_path.exists():
        raise FileExistsError
    key_pair = RSA.generate(3072)
    private_key = key_pair.export_key().decode("ascii")
    public_key = key_pair.public_key().export_key().decode("ascii")
    with open(private_key_path, "w") as fp:
        fp.write(private_key)
    with open(public_key_path, "w") as fp:
        fp.write(public_key)


def load_key(key_path: str = None):
    if key_path is None:
        return None
    with open(key_path) as fp:
        return RSA.import_key(fp.read())


def load_key_pem(key_path: str = None):
    if key_path is None:
        return ""
    with open(key_path) as fp:
        return fp.read()


def import_key(key_pem: str = None):
    if key_pem is None or key_pem == "":
        return None
    else:
        return RSA.import_key(key_pem)
