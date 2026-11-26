from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from ninja import Router
from ninja.errors import HttpError

from api.auth import (
    JWTAuth,
    REFRESH_COOKIE_NAME,
    clear_refresh_cookie,
    create_access_token,
    is_web_client,
    issue_refresh_token,
    revoke_all_user_tokens,
    revoke_refresh_token,
    rotate_refresh_token,
    set_refresh_cookie,
)
from api.schemas.auth import (
    LoginIn,
    LogoutIn,
    MessageOut,
    PasswordResetConfirmIn,
    PasswordResetRequestIn,
    RefreshIn,
    TokenOut,
    UserMeOut,
)
from api.serializers import build_user_me

router = Router()


def _authenticate_email_or_username(identifier: str, password: str):
    cleaned = (identifier or "").strip()
    if not cleaned or not password:
        return None

    user = authenticate(username=cleaned, password=password)
    if user is not None:
        return user

    User = get_user_model()
    matched = User.objects.filter(email__iexact=cleaned).first()
    if matched is not None:
        return authenticate(username=matched.username, password=password)
    return None


@router.post("/login", response=TokenOut)
def login(request, payload: LoginIn, response: HttpResponse):
    user = _authenticate_email_or_username(payload.email, payload.password)
    if user is None or not user.is_active:
        raise HttpError(401, "Invalid email or password.")

    access_token, expires_in = create_access_token(user)
    raw_refresh, _ = issue_refresh_token(user, device_label=payload.device_label)
    web = is_web_client(request)
    if web:
        set_refresh_cookie(response, raw_refresh)

    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "refresh_token": None if web else raw_refresh,
        "user": build_user_me(user),
    }


@router.post("/refresh", response=TokenOut)
def refresh(request, response: HttpResponse, payload: RefreshIn | None = None):
    raw_token = (payload.refresh_token if payload else None) or request.COOKIES.get(
        REFRESH_COOKIE_NAME
    )
    if not raw_token:
        raise HttpError(401, "Refresh token is required.")

    rotated = rotate_refresh_token(raw_token)
    if rotated is None:
        clear_refresh_cookie(response)
        raise HttpError(401, "Invalid or expired refresh token.")

    user, new_refresh, _ = rotated
    access_token, expires_in = create_access_token(user)
    web = is_web_client(request)
    if web:
        set_refresh_cookie(response, new_refresh)

    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "refresh_token": None if web else new_refresh,
        "user": build_user_me(user),
    }


@router.post("/logout", response=MessageOut)
def logout(request, response: HttpResponse, payload: LogoutIn | None = None):
    raw_token = (payload.refresh_token if payload else None) or request.COOKIES.get(
        REFRESH_COOKIE_NAME
    )
    if raw_token:
        revoke_refresh_token(raw_token)
    clear_refresh_cookie(response)
    return {"detail": "Logged out successfully."}


@router.get("/me", response=UserMeOut, auth=JWTAuth())
def me(request):
    return build_user_me(request.auth)


@router.post("/password-reset", response=MessageOut)
def password_reset_request(request, payload: PasswordResetRequestIn):
    email = (payload.email or "").strip().lower()
    if email:
        form = PasswordResetForm({"email": email})
        if form.is_valid():
            form.save(
                request=request,
                use_https=request.is_secure(),
                email_template_name="registration/password_reset_email.html",
            )
    return {
        "detail": "If an account exists for that email address, password reset instructions have been sent."
    }


@router.post("/password-reset/confirm", response=MessageOut)
def password_reset_confirm(request, payload: PasswordResetConfirmIn):
    User = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(payload.uid))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        raise HttpError(400, "Invalid or expired password reset link.")

    if not default_token_generator.check_token(user, payload.token):
        raise HttpError(400, "Invalid or expired password reset link.")

    try:
        validate_password(payload.new_password, user=user)
    except ValidationError as exc:
        raise HttpError(400, " ".join(exc.messages))

    user.set_password(payload.new_password)
    user.save(update_fields=["password"])
    revoke_all_user_tokens(user)

    return {"detail": "Password has been reset successfully."}
