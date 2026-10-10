"""Token based login (replaces the desktop login window, ACEest v3.1.2)."""
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

TOKEN_MAX_AGE = 8 * 3600  # seconds


def make_token(secret, username, role):
    return URLSafeTimedSerializer(secret, salt="aceest-auth").dumps(
        {"username": username, "role": role})


def verify_token(secret, token):
    """Return {'username', 'role'} or None for a missing/invalid/expired token."""
    if not token:
        return None
    try:
        return URLSafeTimedSerializer(secret, salt="aceest-auth").loads(
            token, max_age=TOKEN_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
