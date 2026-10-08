"""Short-code generation and referrer parsing (pure functions, easy to unit test)."""
import secrets
import string
from urllib.parse import urlparse

ALPHABET = string.ascii_letters + string.digits  # 62 characters
CODE_LENGTH = 7  # 62^7 ≈ 3.5 trillion combinations


def generate_code(length: int = CODE_LENGTH) -> str:
    # secrets (not random) so codes can't be predicted from earlier ones.
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def referrer_host(referer_header: str | None) -> str | None:
    """Keep only the host of the Referer header (privacy: no paths or query strings)."""
    if not referer_header:
        return None
    try:
        host = urlparse(referer_header.strip()).hostname
    except ValueError:
        return None
    return host[:255] if host else None
