import datetime
import hashlib
import secrets

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import transaction
from django.utils import timezone
from ninja.security import HttpBearer

from api.models import RefreshToken

ACCESS_TOKEN_TTL_SECONDS = 15 * 60
REFRESH_TOKEN_TTL_DAYS = 60
REFRESH_COOKIE_NAME = "hg_refresh_token"
REFRESH_COOKIE_PATH = "/v1/auth/"


def _signing_key() -> bytes:
    raw = getattr(settings, "JWT_SIGNING_KEY", None) or settings.SECRET_KEY
    return hashlib.sha256(f"highgate-jwt-v1:{raw}".encode("utf-8")).digest()


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_access_token(user) -> tuple[str, int]:
    """
    Create a short-lived HS256 JWT using explicit UTC timestamps so expiration
    remains exact even when Django settings.USE_TZ is False.
    """
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    exp_utc = now_utc + datetime.timedelta(seconds=ACCESS_TOKEN_TTL_SECONDS)
    payload = {
        "sub": str(user.id),
        "type": "access",
        "iat": int(now_utc.timestamp()),
        "exp": int(exp_utc.timestamp()),
    }
    encoded = jwt.encode(payload, _signing_key(), algorithm="HS256")
    return encoded, ACCESS_TOKEN_TTL_SECONDS


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, _signing_key(), algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != "access" or not payload.get("sub"):
        return None
    return payload


def issue_refresh_token(user, device_label: str = "") -> tuple[str, RefreshToken]:
    raw_token = secrets.token_urlsafe(48)
    record = RefreshToken.objects.create(
        user=user,
        token_hash=hash_refresh_token(raw_token),
        device_label=(device_label or "")[:120],
        expires_at=timezone.now() + datetime.timedelta(days=REFRESH_TOKEN_TTL_DAYS),
    )
    return raw_token, record


def rotate_refresh_token(
    raw_token: str, device_label: str | None = None
) -> tuple[object, str, RefreshToken] | None:
    if not raw_token:
        return None
    token_hash = hash_refresh_token(raw_token)
    with transaction.atomic():
        record = (
            RefreshToken.objects.select_related("user")
            .select_for_update()
            .filter(token_hash=token_hash)
            .first()
        )
        if record is None or not record.is_valid() or not record.user.is_active:
            return None

        record.revoked_at = timezone.now()
        record.save(update_fields=["revoked_at"])

        new_raw, new_record = issue_refresh_token(
            record.user,
            device_label=device_label if device_label is not None else record.device_label,
        )
        return record.user, new_raw, new_record


def revoke_refresh_token(raw_token: str) -> None:
    if not raw_token:
        return
    RefreshToken.objects.filter(
        token_hash=hash_refresh_token(raw_token),
        revoked_at__isnull=True,
    ).update(revoked_at=timezone.now())


def revoke_all_user_tokens(user, exclude_hash: str | None = None) -> None:
    qs = RefreshToken.objects.filter(user=user, revoked_at__isnull=True)
    if exclude_hash:
        qs = qs.exclude(token_hash=exclude_hash)
    qs.update(revoked_at=timezone.now())


def is_web_client(request) -> bool:
    return request.headers.get("X-Client-Platform", "").strip().lower() == "web"


def set_refresh_cookie(response, raw_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_token,
        max_age=REFRESH_TOKEN_TTL_DAYS * 86400,
        path=REFRESH_COOKIE_PATH,
        secure=not settings.DEBUG,
        httponly=True,
        samesite="Lax",
    )


def clear_refresh_cookie(response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        samesite="Lax",
    )


class JWTAuth(HttpBearer):
    """Requires a valid access JWT and resolves the corresponding active User."""

    def authenticate(self, request, token: str):
        payload = decode_access_token(token)
        if payload is None:
            return None
        try:
            user_id = int(payload["sub"])
        except (TypeError, ValueError):
            return None

        User = get_user_model()
        user = User.objects.filter(pk=user_id, is_active=True).first()
        if user is not None:
            request.user = user
        return user


class OptionalJWTAuth(JWTAuth):
    """
    Allows unauthenticated public requests when no Authorization header is sent,
    but rejects expired or invalid Bearer tokens with 401 so clients refresh instead
    of silently falling back to anonymous surname masking.
    """

    def __call__(self, request):
        auth_header = request.headers.get(self.header)
        if not auth_header:
            anon = AnonymousUser()
            request.user = anon
            return anon
        return super().__call__(request)


def is_authenticated_request(request) -> bool:
    auth_obj = getattr(request, "auth", None)
    return bool(auth_obj and getattr(auth_obj, "is_authenticated", False))
