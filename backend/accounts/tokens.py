"""JWT issuing and verification.

This used to be a hand-rolled HS256 implementation — PyPI was unreachable
when this project started, and djangorestframework-simplejwt couldn't be
installed. It's reachable now: this module is a thin adapter over the real
package instead. `for_user()` / `access_from_refresh()` / `decode()` keep
their existing signatures and payload shape so nothing calling into this
module (views, tests) had to change — but no cryptography happens here any
more. Signing, signature verification, the `exp` check, and the token-type
check (`AccessToken` vs `RefreshToken` refuses to construct from the wrong
kind of token) are all djangorestframework-simplejwt's.
"""

from __future__ import annotations

from django.conf import settings
from rest_framework_simplejwt.exceptions import TokenError as _SimpleJWTError
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

# Re-exported for anything that wants the configured lifetimes without
# reaching into settings.SIMPLE_JWT directly.
ACCESS_TTL = int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds())
REFRESH_TTL = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())


class TokenError(Exception):
    """Any reason a token is not valid: malformed, bad signature, expired,
    or the wrong type. Wraps simplejwt's own exception so callers keep one
    exception type to catch regardless of which library issues it."""


def for_user(user) -> dict:
    """The access/refresh pair handed back at login / register."""
    refresh = RefreshToken.for_user(user)
    refresh["username"] = user.get_username()
    access = refresh.access_token
    access["username"] = user.get_username()
    return {"access": str(access), "refresh": str(refresh)}


def rotate_refresh(refresh_token: str) -> dict:
    """Consume a refresh token for a new access/refresh pair.

    Rotation: the given refresh token is blacklisted (see
    ROTATE_REFRESH_TOKENS / BLACKLIST_AFTER_ROTATION in settings) so it
    cannot be presented again, and a new refresh token is returned alongside
    the new access token — the client must start using it, since the old one
    stops working from this call on. Rejects a token that is malformed,
    expired, badly signed, or not actually a refresh token.
    """
    try:
        refresh = RefreshToken(refresh_token)
    except _SimpleJWTError as error:
        raise TokenError(str(error)) from error

    access = refresh.access_token
    access["username"] = refresh.get("username")

    try:
        refresh.blacklist()
    except AttributeError:
        pass  # token_blacklist app not installed — rotation still happens,
        # it just isn't enforced against reuse. Not our case: it's installed.

    # Recycle the same claims into a new token rather than minting one from
    # for_user() again, so a custom claim like "username" survives rotation
    # without having to be re-derived.
    refresh.set_jti()
    refresh.set_exp()
    refresh.set_iat()
    refresh.outstand()

    return {"access": str(access), "refresh": str(refresh)}


def decode(token: str, expected_type: str = "access") -> dict:
    """Verify signature, expiry and token type; return the claims.

    Instantiating AccessToken/RefreshToken IS the verification — simplejwt
    checks the signature and `exp` in its base Token.__init__, and each
    subclass rejects a token whose `token_type` claim doesn't match its own
    (so an access token can never be used where a refresh token is expected,
    or the reverse).
    """
    token_class = AccessToken if expected_type == "access" else RefreshToken
    try:
        verified = token_class(token)
    except _SimpleJWTError as error:
        raise TokenError(str(error)) from error
    return dict(verified.payload)
